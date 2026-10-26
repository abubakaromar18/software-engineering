namespace MiniIoC;

/// <summary>Convenience resolution helpers for any <see cref="IServiceProvider"/>.</summary>
public static class ServiceProviderExtensions
{
    /// <summary>Resolves <typeparamref name="T"/> or returns <c>null</c> if it is not registered.</summary>
    public static T? GetService<T>(this IServiceProvider provider) where T : class =>
        (T?)provider.GetService(typeof(T));

    /// <summary>Resolves <paramref name="serviceType"/> or throws if it is not registered.</summary>
    /// <exception cref="UnresolvableServiceException">No registration exists.</exception>
    public static object GetRequiredService(this IServiceProvider provider, Type serviceType)
    {
        ArgumentNullException.ThrowIfNull(provider);
        return provider.GetService(serviceType)
            ?? throw new UnresolvableServiceException(
                serviceType, $"No service for type '{TypeNames.Pretty(serviceType)}' has been registered.");
    }

    /// <summary>Resolves <typeparamref name="T"/> or throws if it is not registered.</summary>
    public static T GetRequiredService<T>(this IServiceProvider provider) where T : class =>
        (T)provider.GetRequiredService(typeof(T));

    /// <summary>Resolves every registration of <typeparamref name="T"/> in registration order.</summary>
    public static IEnumerable<T> GetServices<T>(this IServiceProvider provider) where T : class =>
        provider.GetRequiredService<IEnumerable<T>>();

    /// <summary>Creates a new scope from any provider built by this library.</summary>
    public static IServiceScope CreateScope(this IServiceProvider provider) =>
        provider.GetRequiredService<IServiceScopeFactory>().CreateScope();
}
