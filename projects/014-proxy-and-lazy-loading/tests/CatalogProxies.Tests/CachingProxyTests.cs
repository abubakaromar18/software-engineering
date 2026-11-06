using CatalogProxies.Caching;
using CatalogProxies.Domain;
using CatalogProxies.Proxies;
using CatalogProxies.Tests.TestDoubles;

namespace CatalogProxies.Tests;

public class CachingProxyTests
{
    private static readonly TimeSpan Ttl = TimeSpan.FromSeconds(30);

    private readonly SpyRepository _store = new(Catalog.All);
    private readonly ManualTimeProvider _clock = new();

    [Fact]
    public async Task A_repeated_read_is_served_from_the_cache()
    {
        var cache = Create();

        var first = await cache.GetByIdAsync(Catalog.KeyboardId);
        var second = await cache.GetByIdAsync(Catalog.KeyboardId);

        Assert.Same(first, second);
        Assert.Equal(1, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
        Assert.Equal(new CacheStatistics(Hits: 1, Misses: 1, Coalesced: 0, Evictions: 0, Invalidations: 0), cache.Statistics);
        Assert.Equal(0.5, cache.Statistics.HitRatio);
    }

    [Fact]
    public async Task Entries_expire_after_the_time_to_live()
    {
        var cache = Create();
        await cache.GetByIdAsync(Catalog.KeyboardId);

        _clock.Advance(Ttl - TimeSpan.FromSeconds(1));
        await cache.GetByIdAsync(Catalog.KeyboardId);
        Assert.Equal(1, _store.Calls(nameof(IProductRepository.GetByIdAsync)));

        _clock.Advance(TimeSpan.FromSeconds(1));
        await cache.GetByIdAsync(Catalog.KeyboardId);
        Assert.Equal(2, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
    }

    [Theory]
    [InlineData(true, 1)]
    [InlineData(false, 2)]
    public async Task Not_found_results_are_cached_only_when_negative_caching_is_on(bool cacheMisses, int expectedStoreCalls)
    {
        var cache = Create(new CacheOptions { TimeToLive = Ttl, CacheMisses = cacheMisses });

        Assert.Null(await cache.GetByIdAsync(Catalog.MissingId));
        Assert.Null(await cache.GetByIdAsync(Catalog.MissingId));

        Assert.Equal(expectedStoreCalls, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
    }

    [Fact]
    public async Task Concurrent_misses_for_the_same_key_reach_the_store_once()
    {
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        _store.BeforeCall = _ => release.Task;
        var cache = Create();

        var readers = Enumerable.Range(0, 25).Select(_ => cache.GetByIdAsync(Catalog.DeskId)).ToArray();
        release.SetResult();
        var results = await Task.WhenAll(readers);

        Assert.All(results, p => Assert.Equal(Catalog.Desk, p));
        Assert.Equal(1, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
        Assert.Equal(1, cache.Statistics.Misses);
        Assert.Equal(24, cache.Statistics.Coalesced);
    }

    [Fact]
    public async Task A_failed_load_is_not_cached()
    {
        var fail = true;
        _store.BeforeCall = _ => fail ? Task.FromException(new IOException("disk on fire")) : Task.CompletedTask;
        var cache = Create();

        await Assert.ThrowsAsync<IOException>(() => cache.GetByIdAsync(Catalog.KeyboardId));
        fail = false;

        Assert.Equal(Catalog.Keyboard, await cache.GetByIdAsync(Catalog.KeyboardId));
        Assert.Equal(2, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
    }

    [Fact]
    public async Task Saving_invalidates_the_product_and_every_category_list()
    {
        var cache = Create();
        await cache.GetByIdAsync(Catalog.MouseId);
        await cache.ListByCategoryAsync("Peripherals");
        await cache.ListByCategoryAsync("Furniture");

        // The mouse moves to Furniture: both lists are now out of date.
        await cache.SaveAsync(new Product(Catalog.MouseId, "Wireless mouse", "Furniture", 45m, 18m));

        Assert.Equal(45m, (await cache.GetByIdAsync(Catalog.MouseId))!.Price);
        Assert.Single(await cache.ListByCategoryAsync("Peripherals"));
        Assert.Equal(2, (await cache.ListByCategoryAsync("Furniture")).Count);
        Assert.Equal(3, cache.Statistics.Invalidations);
    }

    [Fact]
    public async Task Deleting_invalidates_the_product()
    {
        var cache = Create();
        await cache.GetByIdAsync(Catalog.DeskId);

        Assert.True(await cache.DeleteAsync(Catalog.DeskId));

        Assert.Null(await cache.GetByIdAsync(Catalog.DeskId));
    }

    [Fact]
    public async Task A_write_during_an_in_flight_read_stops_the_stale_result_being_cached()
    {
        var holdReads = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        _store.BeforeCall = method => method == nameof(IProductRepository.GetByIdAsync) ? holdReads.Task : Task.CompletedTask;
        var cache = Create();

        // The read is held inside the store while the write happens. Whatever it returns, it
        // must not be cached: the next read has to go back to the store.
        var staleRead = cache.GetByIdAsync(Catalog.KeyboardId);
        await cache.SaveAsync(Catalog.Keyboard.WithCostPrice(70m));
        holdReads.SetResult();
        await staleRead;

        _store.BeforeCall = null;
        Assert.Equal(70m, (await cache.GetByIdAsync(Catalog.KeyboardId))!.CostPrice);
        Assert.Equal(2, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
    }

    [Fact]
    public async Task The_least_recently_used_entry_is_evicted_when_full()
    {
        var cache = Create(new CacheOptions { TimeToLive = Ttl, MaxEntries = 2 });
        await cache.GetByIdAsync(Catalog.KeyboardId);
        await cache.GetByIdAsync(Catalog.MouseId);
        await cache.GetByIdAsync(Catalog.KeyboardId); // keyboard is now the most recently used
        await cache.GetByIdAsync(Catalog.DeskId);     // evicts the mouse

        await cache.GetByIdAsync(Catalog.KeyboardId);
        await cache.GetByIdAsync(Catalog.MouseId);

        Assert.Equal(4, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
        Assert.Equal(2, cache.Statistics.Evictions); // the mouse, then the desk
    }

    [Fact]
    public async Task Category_keys_ignore_case_and_surrounding_spaces()
    {
        var cache = Create();

        await cache.ListByCategoryAsync("Peripherals");
        await cache.ListByCategoryAsync("  PERIPHERALS ");

        Assert.Equal(1, _store.Calls(nameof(IProductRepository.ListByCategoryAsync)));
    }

    [Fact]
    public async Task Cached_lists_cannot_be_modified_by_callers()
    {
        var cache = Create();

        var list = await cache.ListByCategoryAsync("Peripherals");

        Assert.IsNotType<List<Product>>(list);
        Assert.Throws<NotSupportedException>(() => ((IList<Product>)list).Add(Catalog.Desk));
    }

    [Fact]
    public async Task A_cancelled_caller_does_not_stop_the_load_being_cached_for_others()
    {
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        _store.BeforeCall = _ => release.Task;
        var cache = Create();

        using var cts = new CancellationTokenSource();
        var cancelled = cache.GetByIdAsync(Catalog.KeyboardId, cts.Token);
        await cts.CancelAsync();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => cancelled);

        release.SetResult();
        Assert.Equal(Catalog.Keyboard, await cache.GetByIdAsync(Catalog.KeyboardId));
        Assert.Equal(1, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
    }

    [Fact]
    public void Invalid_options_are_rejected()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() => _ = new CacheOptions { TimeToLive = TimeSpan.Zero });
        Assert.Throws<ArgumentOutOfRangeException>(() => _ = new CacheOptions { MaxEntries = 0 });
    }

    private CachingRepositoryProxy Create(CacheOptions? options = null) =>
        new(_store, options ?? new CacheOptions { TimeToLive = Ttl }, _clock);
}
