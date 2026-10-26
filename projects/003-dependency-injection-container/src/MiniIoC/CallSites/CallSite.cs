using System.Reflection;

namespace MiniIoC.CallSites;

/// <summary>
/// Identifies one cached instance: a registration (its index in the collection) closed
/// over a concrete service type. Open generics produce one key per closed type, so
/// <c>Repository&lt;User&gt;</c> and <c>Repository&lt;Order&gt;</c> are separate singletons.
/// </summary>
internal readonly record struct ServiceCacheKey(Type ServiceType, int Slot);

/// <summary>
/// A node in the pre-computed resolution plan ("call site") of a service. Plans are
/// built once per service type, validated (cycles, captive dependencies) at build time
/// and then executed many times by <see cref="CallSiteResolver"/>.
/// </summary>
internal abstract class CallSite(Type serviceType, ServiceLifetime lifetime, ServiceCacheKey cacheKey)
{
    public Type ServiceType { get; } = serviceType;

    public ServiceLifetime Lifetime { get; } = lifetime;

    public ServiceCacheKey CacheKey { get; } = cacheKey;

    /// <summary>The children this site needs before it can be activated.</summary>
    public virtual IReadOnlyList<CallSite> Dependencies => [];

    /// <summary>
    /// The first scoped service reachable from this site (including itself), or null.
    /// Used to detect singletons that would capture a scoped instance.
    /// </summary>
    public Type? ScopedDependency =>
        Lifetime == ServiceLifetime.Scoped
            ? ServiceType
            : Dependencies.Select(d => d.ScopedDependency).FirstOrDefault(t => t is not null);
}

/// <summary>Activate a concrete type through a selected public constructor.</summary>
internal sealed class ConstructorCallSite(
    Type serviceType,
    ServiceLifetime lifetime,
    ServiceCacheKey cacheKey,
    ConstructorInfo constructor,
    IReadOnlyList<CallSite> parameters) : CallSite(serviceType, lifetime, cacheKey)
{
    public ConstructorInfo Constructor { get; } = constructor;

    public override IReadOnlyList<CallSite> Dependencies { get; } = parameters;
}

/// <summary>Invoke a user factory. Its dependencies are opaque until it runs.</summary>
internal sealed class FactoryCallSite(
    Type serviceType,
    ServiceLifetime lifetime,
    ServiceCacheKey cacheKey,
    Func<IServiceProvider, object> factory) : CallSite(serviceType, lifetime, cacheKey)
{
    public Func<IServiceProvider, object> Factory { get; } = factory;
}

/// <summary>Return a caller-owned instance as-is.</summary>
internal sealed class InstanceCallSite(Type serviceType, ServiceCacheKey cacheKey, object instance)
    : CallSite(serviceType, ServiceLifetime.Singleton, cacheKey)
{
    public object Instance { get; } = instance;
}

/// <summary>Build a <c>T[]</c> from every registration of <c>T</c>.</summary>
internal sealed class EnumerableCallSite(Type serviceType, Type elementType, IReadOnlyList<CallSite> elements)
    : CallSite(serviceType, ServiceLifetime.Transient, new ServiceCacheKey(serviceType, -1))
{
    public Type ElementType { get; } = elementType;

    public override IReadOnlyList<CallSite> Dependencies { get; } = elements;
}

/// <summary>A constructor parameter with a default value and no registration.</summary>
internal sealed class DefaultValueCallSite(Type serviceType, object? value)
    : CallSite(serviceType, ServiceLifetime.Transient, new ServiceCacheKey(serviceType, -1))
{
    public object? Value { get; } = value;
}

/// <summary>
/// Resolves <see cref="IServiceProvider"/> to the scope doing the resolving. Marked
/// transient so it never counts as a captured scoped dependency: singletons are activated
/// by the root scope, so a singleton asking for the provider safely receives the root.
/// </summary>
internal sealed class ServiceProviderCallSite()
    : CallSite(typeof(IServiceProvider), ServiceLifetime.Transient, new ServiceCacheKey(typeof(IServiceProvider), -1));

/// <summary>Resolves <see cref="IServiceScopeFactory"/> to the container.</summary>
internal sealed class ScopeFactoryCallSite()
    : CallSite(typeof(IServiceScopeFactory), ServiceLifetime.Singleton, new ServiceCacheKey(typeof(IServiceScopeFactory), -1));
