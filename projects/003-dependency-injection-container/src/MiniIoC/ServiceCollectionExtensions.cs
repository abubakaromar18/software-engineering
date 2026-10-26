namespace MiniIoC;

/// <summary>Strongly typed registration helpers.</summary>
public static class ServiceCollectionExtensions
{
    // ---- by type -----------------------------------------------------------

    /// <summary>Registers <typeparamref name="TImplementation"/> as a singleton <typeparamref name="TService"/>.</summary>
    public static ServiceCollection AddSingleton<TService, TImplementation>(this ServiceCollection services)
        where TService : class where TImplementation : class, TService =>
        services.Add(ServiceDescriptor.Describe(typeof(TService), typeof(TImplementation), ServiceLifetime.Singleton));

    /// <summary>Registers <typeparamref name="TImplementation"/> as a scoped <typeparamref name="TService"/>.</summary>
    public static ServiceCollection AddScoped<TService, TImplementation>(this ServiceCollection services)
        where TService : class where TImplementation : class, TService =>
        services.Add(ServiceDescriptor.Describe(typeof(TService), typeof(TImplementation), ServiceLifetime.Scoped));

    /// <summary>Registers <typeparamref name="TImplementation"/> as a transient <typeparamref name="TService"/>.</summary>
    public static ServiceCollection AddTransient<TService, TImplementation>(this ServiceCollection services)
        where TService : class where TImplementation : class, TService =>
        services.Add(ServiceDescriptor.Describe(typeof(TService), typeof(TImplementation), ServiceLifetime.Transient));

    // ---- self registration -------------------------------------------------

    /// <summary>Registers a concrete type as a singleton of itself.</summary>
    public static ServiceCollection AddSingleton<TService>(this ServiceCollection services) where TService : class =>
        services.AddSingleton<TService, TService>();

    /// <summary>Registers a concrete type as a scoped service of itself.</summary>
    public static ServiceCollection AddScoped<TService>(this ServiceCollection services) where TService : class =>
        services.AddScoped<TService, TService>();

    /// <summary>Registers a concrete type as a transient service of itself.</summary>
    public static ServiceCollection AddTransient<TService>(this ServiceCollection services) where TService : class =>
        services.AddTransient<TService, TService>();

    // ---- factories ---------------------------------------------------------

    /// <summary>Registers a singleton built by <paramref name="factory"/>.</summary>
    public static ServiceCollection AddSingleton<TService>(
        this ServiceCollection services, Func<IServiceProvider, TService> factory) where TService : class =>
        services.Add(ServiceDescriptor.FromFactory(typeof(TService), factory, ServiceLifetime.Singleton));

    /// <summary>Registers a scoped service built by <paramref name="factory"/>.</summary>
    public static ServiceCollection AddScoped<TService>(
        this ServiceCollection services, Func<IServiceProvider, TService> factory) where TService : class =>
        services.Add(ServiceDescriptor.FromFactory(typeof(TService), factory, ServiceLifetime.Scoped));

    /// <summary>Registers a transient service built by <paramref name="factory"/>.</summary>
    public static ServiceCollection AddTransient<TService>(
        this ServiceCollection services, Func<IServiceProvider, TService> factory) where TService : class =>
        services.Add(ServiceDescriptor.FromFactory(typeof(TService), factory, ServiceLifetime.Transient));

    // ---- instances and open generics ---------------------------------------

    /// <summary>Registers an existing instance. The container does not take ownership of it.</summary>
    public static ServiceCollection AddSingleton<TService>(this ServiceCollection services, TService instance)
        where TService : class =>
        services.Add(ServiceDescriptor.FromInstance(typeof(TService), instance));

    /// <summary>
    /// Registers by runtime type; this is the overload to use for open generics,
    /// e.g. <c>Add(typeof(IRepository&lt;&gt;), typeof(Repository&lt;&gt;), ServiceLifetime.Scoped)</c>.
    /// </summary>
    public static ServiceCollection Add(
        this ServiceCollection services, Type serviceType, Type implementationType, ServiceLifetime lifetime) =>
        services.Add(ServiceDescriptor.Describe(serviceType, implementationType, lifetime));
}
