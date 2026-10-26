namespace MiniIoC.Tests;

public class ConstructorInjectionTests
{
    [Fact]
    public void Injects_constructor_dependencies()
    {
        using var container = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddTransient<IGreeter, Greeter>()
            .BuildServiceProvider();

        var greeter = container.GetRequiredService<IGreeter>();

        Assert.Equal("Hello Ada, it is 2026", greeter.Greet("Ada"));
    }

    [Fact]
    public void Picks_the_greediest_satisfiable_constructor()
    {
        using var partial = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddTransient<MultiCtor>()
            .BuildServiceProvider();
        using var full = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddTransient<IGreeter, Greeter>()
            .AddTransient<MultiCtor>()
            .BuildServiceProvider();

        Assert.Equal("clock", partial.GetRequiredService<MultiCtor>().Used);
        Assert.Equal("clock+greeter", full.GetRequiredService<MultiCtor>().Used);
    }

    [Fact]
    public void Unregistered_optional_parameters_use_their_defaults()
    {
        using var container = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddTransient<WithOptional>()
            .BuildServiceProvider();

        var service = container.GetRequiredService<WithOptional>();

        Assert.IsType<FixedClock>(service.Clock);
        Assert.Equal(3, service.Retries);
        Assert.Null(service.Name);
    }

    [Fact]
    public void Ambiguous_constructors_are_rejected()
    {
        var services = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddSingleton<IUnitOfWork, UnitOfWork>()
            .AddTransient<Ambiguous>();

        var ex = Assert.Throws<ContainerValidationException>(() => services.BuildServiceProvider());
        Assert.Contains("Ambiguous constructors on 'Ambiguous'", ex.Message);
    }

    [Fact]
    public void Missing_dependency_reports_parameter_and_path()
    {
        var services = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddTransient<IGreeter, Greeter>()
            .AddTransient<NeedsMissing>();

        using var container = services.BuildServiceProvider(new ContainerOptions { ValidateOnBuild = false });

        var ex = Assert.Throws<UnresolvableServiceException>(() => container.GetService(typeof(NeedsMissing)));
        Assert.Equal(typeof(IDisposable), ex.ServiceType);
        Assert.Contains("parameter 'missing' of 'NeedsMissing'", ex.Message);
        Assert.Contains("Resolution path: NeedsMissing", ex.Message);
    }

    [Fact]
    public void Type_without_public_constructor_is_rejected()
    {
        var services = new ServiceCollection().AddTransient<NoPublicCtor>();

        var ex = Assert.Throws<ContainerValidationException>(() => services.BuildServiceProvider());
        Assert.Contains("has no public constructor", ex.Message);
    }

    [Fact]
    public void Constructor_exceptions_are_unwrapped()
    {
        using var container = new ServiceCollection().AddTransient<ThrowingCtor>().BuildServiceProvider();

        var ex = Assert.Throws<InvalidOperationException>(() => container.GetService(typeof(ThrowingCtor)));
        Assert.Equal("boom", ex.Message);
    }

    [Fact]
    public void Factory_registration_receives_the_resolving_provider()
    {
        using var container = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddTransient<IGreeter>(sp => new Greeter(sp.GetRequiredService<IClock>()))
            .BuildServiceProvider();

        var greeter = (Greeter)container.GetRequiredService<IGreeter>();

        Assert.Same(container.GetRequiredService<IClock>(), greeter.Clock);
    }

    [Fact]
    public void Factory_returning_null_is_an_error()
    {
        using var container = new ServiceCollection()
            .AddTransient<IClock>(_ => null!)
            .BuildServiceProvider();

        var ex = Assert.Throws<ContainerException>(() => container.GetService(typeof(IClock)));
        Assert.Contains("returned null", ex.Message);
    }
}
