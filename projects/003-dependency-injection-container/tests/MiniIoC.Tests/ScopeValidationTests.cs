namespace MiniIoC.Tests;

public class ScopeValidationTests
{
    [Fact]
    public void Resolving_scoped_from_root_is_rejected()
    {
        using var container = new ServiceCollection().AddScoped<IUnitOfWork, UnitOfWork>().BuildServiceProvider();

        var ex = Assert.Throws<ScopeValidationException>(() => container.GetService(typeof(IUnitOfWork)));
        Assert.Contains("from the root provider", ex.Message);
    }

    [Fact]
    public void Resolving_scoped_from_root_is_allowed_when_validation_is_off()
    {
        using var container = new ServiceCollection()
            .AddScoped<IUnitOfWork, UnitOfWork>()
            .BuildServiceProvider(new ContainerOptions { ValidateScopes = false });

        Assert.Same(container.GetRequiredService<IUnitOfWork>(), container.GetRequiredService<IUnitOfWork>());
    }

    [Fact]
    public void Singleton_capturing_scoped_is_a_build_error()
    {
        var services = new ServiceCollection()
            .AddScoped<IUnitOfWork, UnitOfWork>()
            .AddSingleton<SingletonNeedsScoped>();

        var ex = Assert.Throws<ContainerValidationException>(() => services.BuildServiceProvider());
        var error = Assert.IsType<ScopeValidationException>(Assert.Single(ex.Errors));
        Assert.Contains("'SingletonNeedsScoped' cannot depend on scoped service 'IUnitOfWork'", error.Message);
    }

    [Fact]
    public void Captive_dependency_is_detected_through_a_transient()
    {
        var services = new ServiceCollection()
            .AddScoped<IUnitOfWork, UnitOfWork>()
            .AddTransient<TransientNeedsScoped>()
            .AddSingleton<SingletonNeedsTransientNeedsScoped>();

        using var container = services.BuildServiceProvider(new ContainerOptions { ValidateOnBuild = false });
        using var scope = container.CreateScope();

        Assert.Throws<ScopeValidationException>(
            () => scope.ServiceProvider.GetService(typeof(SingletonNeedsTransientNeedsScoped)));
    }

    [Fact]
    public void Captive_dependency_is_detected_through_an_enumerable()
    {
        var services = new ServiceCollection();
        services.Add(ServiceDescriptor.Describe(typeof(PluginConsumer), typeof(PluginConsumer), ServiceLifetime.Singleton));
        services.Add(ServiceDescriptor.Describe(typeof(IPlugin), typeof(ScopedPlugin), ServiceLifetime.Scoped));

        var ex = Assert.Throws<ContainerValidationException>(() => services.BuildServiceProvider());
        Assert.Contains(ex.Errors, e => e is ScopeValidationException);
    }

    [Fact]
    public void Singleton_receiving_IServiceProvider_gets_the_root()
    {
        using var container = new ServiceCollection().AddSingleton<SingletonNeedsProvider>().BuildServiceProvider();
        using var scope = container.CreateScope();

        var singleton = scope.ServiceProvider.GetRequiredService<SingletonNeedsProvider>();

        Assert.NotSame(scope.ServiceProvider, singleton.Provider);
        Assert.Same(container.GetRequiredService<IServiceProvider>(), singleton.Provider);
    }

    private sealed class ScopedPlugin : IPlugin { }

    private sealed class PluginConsumer(IEnumerable<IPlugin> plugins)
    {
        public IEnumerable<IPlugin> Plugins { get; } = plugins;
    }
}
