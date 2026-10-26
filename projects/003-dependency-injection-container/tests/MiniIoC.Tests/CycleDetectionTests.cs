namespace MiniIoC.Tests;

public class CycleDetectionTests
{
    private static readonly ContainerOptions Lazy = new() { ValidateOnBuild = false };

    [Fact]
    public void Detects_an_indirect_cycle_and_reports_the_path()
    {
        using var container = new ServiceCollection()
            .AddTransient<CycleA>().AddTransient<CycleB>().AddTransient<CycleC>()
            .BuildServiceProvider(Lazy);

        var ex = Assert.Throws<CircularDependencyException>(() => container.GetService(typeof(CycleA)));

        Assert.Equal(new[] { typeof(CycleA), typeof(CycleB), typeof(CycleC), typeof(CycleA) }, ex.Path);
        Assert.Equal("Circular dependency detected: CycleA -> CycleB -> CycleC -> CycleA.", ex.Message);
    }

    [Fact]
    public void Path_starts_at_the_cycle_not_at_the_request()
    {
        using var container = new ServiceCollection()
            .AddTransient<CycleA>().AddTransient<CycleB>().AddTransient<CycleC>()
            .BuildServiceProvider(Lazy);

        var ex = Assert.Throws<CircularDependencyException>(() => container.GetService(typeof(CycleB)));

        Assert.Equal(new[] { typeof(CycleB), typeof(CycleC), typeof(CycleA), typeof(CycleB) }, ex.Path);
    }

    [Fact]
    public void Detects_a_self_dependency()
    {
        using var container = new ServiceCollection().AddSingleton<SelfCycle>().BuildServiceProvider(Lazy);

        var ex = Assert.Throws<CircularDependencyException>(() => container.GetService(typeof(SelfCycle)));
        Assert.Equal(new[] { typeof(SelfCycle), typeof(SelfCycle) }, ex.Path);
    }

    [Fact]
    public void Detects_a_cycle_through_IEnumerable()
    {
        using var container = new ServiceCollection()
            .AddTransient<IPlugin, PluginHost>()
            .BuildServiceProvider(Lazy);

        Assert.Throws<CircularDependencyException>(() => container.GetService(typeof(IPlugin)));
    }

    [Fact]
    public void Detects_a_cycle_through_a_factory_at_runtime()
    {
        using var container = new ServiceCollection()
            .AddTransient<IClock>(sp => sp.GetRequiredService<IClock>())
            .BuildServiceProvider();

        var ex = Assert.Throws<CircularDependencyException>(() => container.GetService(typeof(IClock)));
        Assert.Equal(new[] { typeof(IClock), typeof(IClock) }, ex.Path);
    }

    [Fact]
    public void Validate_on_build_reports_cycles_at_startup()
    {
        var services = new ServiceCollection()
            .AddTransient<CycleA>().AddTransient<CycleB>().AddTransient<CycleC>();

        var ex = Assert.Throws<ContainerValidationException>(() => services.BuildServiceProvider());

        Assert.Equal(3, ex.Errors.Count);
        Assert.All(ex.Errors, e => Assert.IsType<CircularDependencyException>(e));
    }

    [Fact]
    public void A_diamond_is_not_a_cycle()
    {
        // Greeter and MultiCtor both depend on IClock; sharing a dependency is fine.
        using var container = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddTransient<IGreeter, Greeter>()
            .AddTransient<MultiCtor>()
            .BuildServiceProvider();

        Assert.Equal("clock+greeter", container.GetRequiredService<MultiCtor>().Used);
    }
}
