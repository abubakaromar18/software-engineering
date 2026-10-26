namespace MiniIoC.Tests;

public class DisposalTests
{
    private static ServiceCollection Services(DisposalLog log) =>
        new ServiceCollection().AddSingleton(log);

    [Fact]
    public void Scope_disposes_its_scoped_instances_in_reverse_creation_order()
    {
        var log = new DisposalLog();
        using var container = Services(log).AddScoped<TrackedA>().AddScoped<TrackedB>().BuildServiceProvider();

        using (var scope = container.CreateScope())
        {
            scope.ServiceProvider.GetRequiredService<TrackedB>(); // creates A first, then B
        }

        Assert.Equal(new[] { "B", "A" }, log.Entries);
    }

    [Fact]
    public void Singletons_outlive_scopes_and_die_with_the_container()
    {
        var log = new DisposalLog();
        var container = Services(log).AddSingleton<TrackedA>().BuildServiceProvider();

        TrackedA a;
        using (var scope = container.CreateScope())
        {
            a = scope.ServiceProvider.GetRequiredService<TrackedA>();
        }

        Assert.False(a.IsDisposed);
        container.Dispose();
        Assert.True(a.IsDisposed);
    }

    [Fact]
    public void Disposable_transients_are_owned_by_the_resolving_scope()
    {
        var log = new DisposalLog();
        using var container = Services(log).AddTransient<TrackedA>().BuildServiceProvider();

        TrackedA first, second;
        using (var scope = container.CreateScope())
        {
            first = scope.ServiceProvider.GetRequiredService<TrackedA>();
            second = scope.ServiceProvider.GetRequiredService<TrackedA>();
        }

        Assert.True(first.IsDisposed);
        Assert.True(second.IsDisposed);
    }

    [Fact]
    public void Registered_instances_are_not_disposed()
    {
        var log = new DisposalLog();
        var instance = new TrackedA(log);
        var container = new ServiceCollection().AddSingleton(instance).BuildServiceProvider();

        container.GetRequiredService<TrackedA>();
        container.Dispose();

        Assert.False(instance.IsDisposed);
    }

    [Fact]
    public void Factory_singletons_are_disposed()
    {
        var log = new DisposalLog();
        var container = new ServiceCollection().AddSingleton(_ => new TrackedA(log)).BuildServiceProvider();

        var a = container.GetRequiredService<TrackedA>();
        container.Dispose();

        Assert.True(a.IsDisposed);
    }

    [Fact]
    public void Resolving_from_a_disposed_scope_throws()
    {
        using var container = new ServiceCollection().AddScoped<IUnitOfWork, UnitOfWork>().BuildServiceProvider();
        var scope = container.CreateScope();
        scope.Dispose();

        Assert.Throws<ObjectDisposedException>(() => scope.ServiceProvider.GetService(typeof(IUnitOfWork)));
    }

    [Fact]
    public void Creating_a_scope_from_a_disposed_container_throws()
    {
        var container = new ServiceCollection().BuildServiceProvider();
        container.Dispose();

        Assert.Throws<ObjectDisposedException>(() => container.CreateScope());
    }

    [Fact]
    public void Dispose_is_idempotent()
    {
        var log = new DisposalLog();
        var container = Services(log).AddSingleton<TrackedA>().BuildServiceProvider();
        container.GetRequiredService<TrackedA>();

        container.Dispose();
        container.Dispose();

        Assert.Equal(new[] { "A" }, log.Entries);
    }

    [Fact]
    public async Task DisposeAsync_handles_async_only_services()
    {
        var log = new DisposalLog();
        var container = Services(log).AddScoped<AsyncOnly>().AddScoped<TrackedA>().BuildServiceProvider();

        await using (var scope = container.CreateScope())
        {
            scope.ServiceProvider.GetRequiredService<AsyncOnly>();
            scope.ServiceProvider.GetRequiredService<TrackedA>();
        }

        Assert.Equal(new[] { "A", "async" }, log.Entries);
        await container.DisposeAsync();
    }

    [Fact]
    public void Sync_dispose_of_async_only_service_explains_what_to_do()
    {
        var log = new DisposalLog();
        using var container = Services(log).AddScoped<AsyncOnly>().BuildServiceProvider();
        var scope = container.CreateScope();
        scope.ServiceProvider.GetRequiredService<AsyncOnly>();

        var ex = Assert.Throws<InvalidOperationException>(scope.Dispose);
        Assert.Contains("Use DisposeAsync", ex.Message);
    }

    [Fact]
    public void A_failing_dispose_does_not_prevent_disposing_the_rest()
    {
        var log = new DisposalLog();
        using var container = Services(log)
            .AddScoped<TrackedA>()
            .AddScoped<FailingDispose>()
            .BuildServiceProvider();
        var scope = container.CreateScope();
        var a = scope.ServiceProvider.GetRequiredService<TrackedA>();
        scope.ServiceProvider.GetRequiredService<FailingDispose>();

        var ex = Assert.Throws<InvalidOperationException>(scope.Dispose);

        Assert.Equal("dispose failed", ex.Message);
        Assert.True(a.IsDisposed);
    }

    [Fact]
    public void Several_failing_disposes_are_aggregated()
    {
        using var container = new ServiceCollection().AddTransient<FailingDispose>().BuildServiceProvider();
        var scope = container.CreateScope();
        scope.ServiceProvider.GetRequiredService<FailingDispose>();
        scope.ServiceProvider.GetRequiredService<FailingDispose>();

        var ex = Assert.Throws<AggregateException>(scope.Dispose);

        Assert.Equal(2, ex.InnerExceptions.Count);
    }
}
