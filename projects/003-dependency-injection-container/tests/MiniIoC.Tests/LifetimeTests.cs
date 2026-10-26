namespace MiniIoC.Tests;

public class LifetimeTests
{
    [Fact]
    public void Transient_returns_a_new_instance_every_time()
    {
        using var container = new ServiceCollection().AddTransient<IClock, FixedClock>().BuildServiceProvider();

        Assert.NotSame(container.GetRequiredService<IClock>(), container.GetRequiredService<IClock>());
    }

    [Fact]
    public void Singleton_is_shared_across_root_and_scopes()
    {
        using var container = new ServiceCollection().AddSingleton<IClock, FixedClock>().BuildServiceProvider();
        using var scope = container.CreateScope();

        var fromRoot = container.GetRequiredService<IClock>();
        Assert.Same(fromRoot, scope.ServiceProvider.GetRequiredService<IClock>());
        Assert.Same(fromRoot, container.GetRequiredService<IClock>());
    }

    [Fact]
    public void Scoped_is_shared_within_a_scope_but_not_across_scopes()
    {
        using var container = new ServiceCollection().AddScoped<IUnitOfWork, UnitOfWork>().BuildServiceProvider();
        using var first = container.CreateScope();
        using var second = container.CreateScope();

        var a1 = first.ServiceProvider.GetRequiredService<IUnitOfWork>();
        var a2 = first.ServiceProvider.GetRequiredService<IUnitOfWork>();
        var b = second.ServiceProvider.GetRequiredService<IUnitOfWork>();

        Assert.Same(a1, a2);
        Assert.NotSame(a1, b);
    }

    [Fact]
    public void Transients_share_the_scoped_instance_of_their_scope()
    {
        using var container = new ServiceCollection()
            .AddScoped<IUnitOfWork, UnitOfWork>()
            .AddTransient<TransientNeedsScoped>()
            .BuildServiceProvider();
        using var scope = container.CreateScope();

        var x = scope.ServiceProvider.GetRequiredService<TransientNeedsScoped>();
        var y = scope.ServiceProvider.GetRequiredService<TransientNeedsScoped>();

        Assert.NotSame(x, y);
        Assert.Same(x.UnitOfWork, y.UnitOfWork);
    }

    [Fact]
    public void Singleton_is_created_exactly_once_under_concurrency()
    {
        using var container = new ServiceCollection().AddSingleton<Counter>().BuildServiceProvider();
        var before = Counter.Created;

        var instances = new Counter[64];
        Parallel.For(0, instances.Length, i => instances[i] = container.GetRequiredService<Counter>());

        Assert.Equal(before + 1, Counter.Created);
        Assert.All(instances, c => Assert.Same(instances[0], c));
    }

    [Fact]
    public void Provider_inside_a_scope_is_that_scope()
    {
        using var container = new ServiceCollection().AddScoped<IUnitOfWork, UnitOfWork>().BuildServiceProvider();
        using var scope = container.CreateScope();

        var provider = scope.ServiceProvider.GetRequiredService<IServiceProvider>();

        Assert.Same(scope.ServiceProvider, provider);
        Assert.Same(
            scope.ServiceProvider.GetRequiredService<IUnitOfWork>(),
            provider.GetRequiredService<IUnitOfWork>());
    }

    [Fact]
    public void Scopes_can_be_created_from_the_resolved_scope_factory()
    {
        using var container = new ServiceCollection().AddScoped<IUnitOfWork, UnitOfWork>().BuildServiceProvider();
        using var outer = container.CreateScope();
        using var nested = outer.ServiceProvider.CreateScope();

        Assert.NotSame(
            outer.ServiceProvider.GetRequiredService<IUnitOfWork>(),
            nested.ServiceProvider.GetRequiredService<IUnitOfWork>());
    }
}
