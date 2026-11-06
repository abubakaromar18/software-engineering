using CatalogProxies.Caching;
using CatalogProxies.Domain;
using CatalogProxies.Dynamic;
using CatalogProxies.Infrastructure;
using CatalogProxies.Security;
using CatalogProxies.Tests.TestDoubles;

namespace CatalogProxies.Tests;

public sealed class CompositionTests : IAsyncDisposable
{
    private readonly SpyRepository _store = new(Catalog.All);
    private readonly InMemoryInvocationSink _sink = new();
    private readonly CatalogComposition _catalog;
    private int _connects;

    public CompositionTests() =>
        _catalog = new CatalogComposition(
            _ =>
            {
                Interlocked.Increment(ref _connects);
                return Task.FromResult<IProductRepository>(_store);
            },
            new CacheOptions { TimeToLive = TimeSpan.FromMinutes(1) },
            _sink,
            new ManualTimeProvider());

    [Fact]
    public void Building_repositories_for_users_does_not_connect()
    {
        _catalog.ForUser(Catalog.Shopper);
        _catalog.ForUser(Catalog.Admin);

        Assert.False(_catalog.IsConnected);
        Assert.Equal(0, _connects);
    }

    [Fact]
    public async Task A_denied_request_is_timed_but_never_connects()
    {
        var anonymous = _catalog.ForUser(Catalog.Anonymous);

        await Assert.ThrowsAsync<AccessDeniedException>(() => anonymous.GetByIdAsync(Catalog.KeyboardId));

        Assert.False(_catalog.IsConnected);
        Assert.Equal(InvocationOutcome.Faulted, Assert.Single(_sink.Records).Outcome);
    }

    [Fact]
    public async Task The_shared_cache_holds_full_products_and_each_user_gets_their_own_view()
    {
        var shopper = _catalog.ForUser(Catalog.Shopper);
        var admin = _catalog.ForUser(Catalog.Admin);

        // The shopper fills the cache first. If redaction happened below the cache,
        // the admin would now get a product with no cost price.
        Assert.Null((await shopper.GetByIdAsync(Catalog.KeyboardId))!.CostPrice);
        Assert.Equal(61m, (await admin.GetByIdAsync(Catalog.KeyboardId))!.CostPrice);

        Assert.Equal(1, _store.Calls(nameof(IProductRepository.GetByIdAsync)));
        Assert.Equal(1, _catalog.CacheStatistics.Hits);
        Assert.Equal(1, _connects);
    }

    [Fact]
    public async Task Writes_go_through_every_layer_and_are_visible_to_other_users()
    {
        var merch = _catalog.ForUser(Catalog.Merchandiser);
        var shopper = _catalog.ForUser(Catalog.Shopper);
        await shopper.GetByIdAsync(Catalog.DeskId);

        await merch.SaveAsync(new Product(Catalog.DeskId, "Standing desk", "Furniture", 549m));

        Assert.Equal(549m, (await shopper.GetByIdAsync(Catalog.DeskId))!.Price);
        Assert.Equal(310m, _store.Stored(Catalog.DeskId)!.CostPrice);
    }

    [Fact]
    public async Task End_to_end_with_the_slow_repository()
    {
        await using var catalog = new CatalogComposition(async ct =>
            await SlowProductRepository.ConnectAsync(Catalog.All, NoLatency.Instance, NoLatency.Instance, ct));
        var shopper = catalog.ForUser(Catalog.Shopper);

        var furniture = await shopper.ListByCategoryAsync("furniture");
        await shopper.ListByCategoryAsync("Furniture");

        Assert.Equal("Standing desk", Assert.Single(furniture).Name);
        Assert.Equal(1, catalog.CacheStatistics.Hits);
    }

    public ValueTask DisposeAsync() => _catalog.DisposeAsync();
}
