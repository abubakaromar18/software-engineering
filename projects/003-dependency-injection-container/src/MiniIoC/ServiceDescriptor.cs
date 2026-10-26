namespace MiniIoC;

/// <summary>
/// An immutable registration: which service type maps to which implementation strategy
/// (a type to construct, a factory, or a pre-built instance) and with which lifetime.
/// </summary>
public sealed class ServiceDescriptor
{
    private ServiceDescriptor(
        Type serviceType,
        ServiceLifetime lifetime,
        Type? implementationType,
        Func<IServiceProvider, object>? factory,
        object? instance)
    {
        ServiceType = serviceType;
        Lifetime = lifetime;
        ImplementationType = implementationType;
        Factory = factory;
        Instance = instance;
    }

    /// <summary>The type consumers ask for.</summary>
    public Type ServiceType { get; }

    /// <summary>How long resolved instances live.</summary>
    public ServiceLifetime Lifetime { get; }

    /// <summary>The concrete type to construct, when registered by type.</summary>
    public Type? ImplementationType { get; }

    /// <summary>The factory to invoke, when registered by factory.</summary>
    public Func<IServiceProvider, object>? Factory { get; }

    /// <summary>The pre-built instance, when registered by instance (always a singleton).</summary>
    public object? Instance { get; }

    /// <summary>True when both the service and implementation are open generic definitions.</summary>
    public bool IsOpenGeneric => ServiceType.IsGenericTypeDefinition;

    /// <summary>Registers <paramref name="implementationType"/> to be constructed for <paramref name="serviceType"/>.</summary>
    /// <exception cref="ArgumentException">The implementation cannot satisfy the service type.</exception>
    public static ServiceDescriptor Describe(Type serviceType, Type implementationType, ServiceLifetime lifetime)
    {
        ArgumentNullException.ThrowIfNull(serviceType);
        ArgumentNullException.ThrowIfNull(implementationType);
        EnsureConstructible(implementationType);

        if (serviceType.IsGenericTypeDefinition || implementationType.IsGenericTypeDefinition)
        {
            EnsureOpenGenericCompatible(serviceType, implementationType);
        }
        else if (!serviceType.IsAssignableFrom(implementationType))
        {
            throw new ArgumentException(
                $"'{TypeNames.Pretty(implementationType)}' is not assignable to '{TypeNames.Pretty(serviceType)}'.",
                nameof(implementationType));
        }

        return new ServiceDescriptor(serviceType, lifetime, implementationType, null, null);
    }

    /// <summary>Registers a factory that builds the service from the resolving provider.</summary>
    public static ServiceDescriptor FromFactory(
        Type serviceType, Func<IServiceProvider, object> factory, ServiceLifetime lifetime)
    {
        ArgumentNullException.ThrowIfNull(serviceType);
        ArgumentNullException.ThrowIfNull(factory);
        if (serviceType.IsGenericTypeDefinition)
        {
            throw new ArgumentException("Factories cannot be registered for open generic types.", nameof(serviceType));
        }

        return new ServiceDescriptor(serviceType, lifetime, null, factory, null);
    }

    /// <summary>
    /// Registers an existing instance as a singleton. The caller keeps ownership, so the
    /// container never disposes it.
    /// </summary>
    public static ServiceDescriptor FromInstance(Type serviceType, object instance)
    {
        ArgumentNullException.ThrowIfNull(serviceType);
        ArgumentNullException.ThrowIfNull(instance);
        if (!serviceType.IsInstanceOfType(instance))
        {
            throw new ArgumentException(
                $"Instance of '{TypeNames.Pretty(instance.GetType())}' is not assignable to '{TypeNames.Pretty(serviceType)}'.",
                nameof(instance));
        }

        return new ServiceDescriptor(serviceType, ServiceLifetime.Singleton, null, null, instance);
    }

    /// <inheritdoc />
    public override string ToString()
    {
        var target = ImplementationType is not null ? TypeNames.Pretty(ImplementationType)
            : Factory is not null ? "factory"
            : "instance";
        return $"{TypeNames.Pretty(ServiceType)} -> {target} ({Lifetime})";
    }

    private static void EnsureConstructible(Type implementationType)
    {
        if (implementationType.IsAbstract || implementationType.IsInterface)
        {
            throw new ArgumentException(
                $"'{TypeNames.Pretty(implementationType)}' must be a concrete class.", nameof(implementationType));
        }
    }

    private static void EnsureOpenGenericCompatible(Type serviceType, Type implementationType)
    {
        if (!serviceType.IsGenericTypeDefinition || !implementationType.IsGenericTypeDefinition)
        {
            throw new ArgumentException(
                "Open generic registrations require both the service and the implementation to be open generic types.");
        }

        if (serviceType.GetGenericArguments().Length != implementationType.GetGenericArguments().Length)
        {
            throw new ArgumentException(
                $"'{TypeNames.Pretty(implementationType)}' and '{TypeNames.Pretty(serviceType)}' must have the same number of type parameters.");
        }

        if (!ImplementsGenericDefinition(implementationType, serviceType))
        {
            throw new ArgumentException(
                $"'{TypeNames.Pretty(implementationType)}' does not implement '{TypeNames.Pretty(serviceType)}'.");
        }
    }

    private static bool ImplementsGenericDefinition(Type implementation, Type definition)
    {
        if (definition.IsInterface)
        {
            return implementation.GetInterfaces()
                .Any(i => i.IsGenericType && i.GetGenericTypeDefinition() == definition);
        }

        for (var current = implementation; current is not null; current = current.BaseType)
        {
            if (current.IsGenericType && current.GetGenericTypeDefinition() == definition)
            {
                return true;
            }
        }

        return false;
    }
}
