using CatalogProxies.Domain;
using CatalogProxies.Infrastructure;
using CatalogProxies.Proxies;
using CatalogProxies.Tests.TestDoubles;

namespace CatalogProxies.Tests;

public class VirtualProxyTests
{
    [Fact]
    public void Creating_the_proxy_does_not_connect()
    {
        var connects = 0;
        var proxy = new VirtualRepositoryProxy(_ =>
        {
            connects++;
            return Task.FromResult<IProductRepository>(new SpyRepository());
        });

        Assert.False(proxy.IsMaterialized);
        Assert.Equal(0, connects);
    }

    [Fact]
    public async Task The_first_call_connects_and_every_call_is_forwarded()
    {
        var connects = 0;
        var real = new SpyRepository(Catalog.All);
        var proxy = new VirtualRepositoryProxy(_ =>
        {
            connects++;
            return Task.FromResult<IProductRepository>(real);
        });

        Assert.Equal(Catalog.Keyboard, await proxy.GetByIdAsync(Catalog.KeyboardId));
        Assert.Equal(2, (await proxy.ListByCategoryAsync("Peripherals")).Count);
        await proxy.SaveAsync(Catalog.Desk.WithCostPrice(1m));
        Assert.True(await proxy.DeleteAsync(Catalog.MouseId));

        Assert.True(proxy.IsMaterialized);
        Assert.Equal(1, connects);
        Assert.Equal(4, real.TotalCalls);
    }

    [Fact]
    public async Task Concurrent_first_calls_connect_only_once()
    {
        var connects = 0;
        var proxy = new VirtualRepositoryProxy(async ct =>
        {
            Interlocked.Increment(ref connects);
            await Task.Delay(30, ct);
            return new SpyRepository(Catalog.All);
        });

        await Task.WhenAll(Enumerable.Range(0, 16).Select(_ => Task.Run(() => proxy.GetByIdAsync(Catalog.DeskId))));

        Assert.Equal(1, connects);
    }

    [Fact]
    public async Task A_failed_connection_surfaces_to_the_caller_and_the_next_call_retries()
    {
        var attempts = 0;
        var proxy = new VirtualRepositoryProxy(_ => ++attempts == 1
            ? Task.FromException<IProductRepository>(new TimeoutException("store unreachable"))
            : Task.FromResult<IProductRepository>(new SpyRepository(Catalog.All)));

        await Assert.ThrowsAsync<TimeoutException>(() => proxy.GetByIdAsync(Catalog.KeyboardId));
        Assert.False(proxy.IsMaterialized);

        Assert.NotNull(await proxy.GetByIdAsync(Catalog.KeyboardId));
        Assert.Equal(2, attempts);
    }

    [Fact]
    public async Task Disposing_an_unused_proxy_never_creates_the_subject()
    {
        var connects = 0;
        var proxy = new VirtualRepositoryProxy(_ =>
        {
            connects++;
            return Task.FromResult<IProductRepository>(new DisposableRepository());
        });

        await proxy.DisposeAsync();

        Assert.Equal(0, connects);
    }

    [Fact]
    public async Task Disposing_a_used_proxy_disposes_the_subject()
    {
        var real = new DisposableRepository();
        var proxy = new VirtualRepositoryProxy(_ => Task.FromResult<IProductRepository>(real));

        await proxy.GetByIdAsync(Catalog.KeyboardId);
        await proxy.DisposeAsync();

        Assert.True(real.Disposed);
    }

    [Fact]
    public async Task Works_in_front_of_the_slow_repository()
    {
        var proxy = new VirtualRepositoryProxy(async ct =>
            await SlowProductRepository.ConnectAsync(Catalog.All, NoLatency.Instance, NoLatency.Instance, ct));

        var peripherals = await proxy.ListByCategoryAsync(" peripherals ");

        Assert.Equal(new[] { Catalog.KeyboardId, Catalog.MouseId }, peripherals.Select(p => p.Id));
    }
}
