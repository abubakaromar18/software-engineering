using System.Collections.Concurrent;
using System.Reflection;

namespace MiniIoC.CallSites;

/// <summary>
/// Turns registrations into validated resolution plans. All structural checks live here
/// (constructor selection, missing dependencies, cycles, captive dependencies) so the
/// runtime resolver can stay a simple interpreter.
/// </summary>
internal sealed class CallSiteFactory
{
    private readonly ServiceDescriptor[] _descriptors;
    private readonly Dictionary<Type, List<int>> _slotsByServiceType = [];
    private readonly bool _validateScopes;

    // Plans are pure functions of the (frozen) registrations, so racing builders produce
    // equivalent results and a lock-free cache is sufficient.
    private readonly ConcurrentDictionary<Type, CallSite?> _serviceCache = new();
    private readonly ConcurrentDictionary<ServiceCacheKey, CallSite> _slotCache = new();

    public CallSiteFactory(ServiceDescriptor[] descriptors, bool validateScopes)
    {
        _descriptors = descriptors;
        _validateScopes = validateScopes;
        for (var slot = 0; slot < descriptors.Length; slot++)
        {
            var key = descriptors[slot].ServiceType;
            if (!_slotsByServiceType.TryGetValue(key, out var slots))
            {
                _slotsByServiceType[key] = slots = [];
            }

            slots.Add(slot);
        }
    }

    /// <summary>Returns the plan for <paramref name="serviceType"/>, or null if it is not registered.</summary>
    public CallSite? GetCallSite(Type serviceType) => GetCallSite(serviceType, ResolutionChain.Empty);

    /// <summary>Plans every closed registration and returns every error found.</summary>
    public IReadOnlyList<ContainerException> ValidateAll()
    {
        var errors = new List<ContainerException>();
        for (var slot = 0; slot < _descriptors.Length; slot++)
        {
            var descriptor = _descriptors[slot];
            if (descriptor.IsOpenGeneric)
            {
                continue; // can only be validated once closed over concrete arguments
            }

            try
            {
                GetSlotCallSite(descriptor, slot, descriptor.ServiceType, ResolutionChain.Empty);
            }
            catch (ContainerException ex)
            {
                errors.Add(ex);
            }
        }

        return errors;
    }

    private CallSite? GetCallSite(Type serviceType, ResolutionChain chain)
    {
        if (_serviceCache.TryGetValue(serviceType, out var cached))
        {
            return cached;
        }

        var site = TryBuiltIn(serviceType)
                   ?? TryExact(serviceType, chain)
                   ?? TryOpenGeneric(serviceType, chain)
                   ?? TryEnumerable(serviceType, chain);
        _serviceCache.TryAdd(serviceType, site);
        return site;
    }

    private bool IsResolvable(Type serviceType) =>
        TryBuiltIn(serviceType) is not null
        || _slotsByServiceType.ContainsKey(serviceType)
        || (serviceType.IsConstructedGenericType
            && (_slotsByServiceType.ContainsKey(serviceType.GetGenericTypeDefinition())
                || serviceType.GetGenericTypeDefinition() == typeof(IEnumerable<>)));

    private static CallSite? TryBuiltIn(Type serviceType)
    {
        if (serviceType == typeof(IServiceProvider))
        {
            return new ServiceProviderCallSite();
        }

        return serviceType == typeof(IServiceScopeFactory) ? new ScopeFactoryCallSite() : null;
    }

    private CallSite? TryExact(Type serviceType, ResolutionChain chain)
    {
        if (!_slotsByServiceType.TryGetValue(serviceType, out var slots))
        {
            return null;
        }

        var last = slots[^1]; // last registration wins
        return GetSlotCallSite(_descriptors[last], last, serviceType, chain);
    }

    private CallSite? TryOpenGeneric(Type serviceType, ResolutionChain chain)
    {
        if (!serviceType.IsConstructedGenericType
            || !_slotsByServiceType.TryGetValue(serviceType.GetGenericTypeDefinition(), out var slots))
        {
            return null;
        }

        // Walk backwards so the last registration that can be closed wins.
        for (var i = slots.Count - 1; i >= 0; i--)
        {
            var site = TryCloseGeneric(slots[i], serviceType, chain);
            if (site is not null)
            {
                return site;
            }
        }

        return null;
    }

    private CallSite? TryCloseGeneric(int slot, Type closedServiceType, ResolutionChain chain)
    {
        var descriptor = _descriptors[slot];
        Type closedImplementation;
        try
        {
            closedImplementation = descriptor.ImplementationType!.MakeGenericType(closedServiceType.GenericTypeArguments);
        }
        catch (ArgumentException)
        {
            return null; // generic constraints not satisfied by these arguments
        }

        var key = new ServiceCacheKey(closedServiceType, slot);
        if (_slotCache.TryGetValue(key, out var cached))
        {
            return cached;
        }

        var inner = chain.Enter(closedServiceType);
        var site = CreateConstructorSite(closedServiceType, descriptor.Lifetime, key, closedImplementation, inner);
        return _slotCache.GetOrAdd(key, site);
    }

    private EnumerableCallSite? TryEnumerable(Type serviceType, ResolutionChain chain)
    {
        if (!serviceType.IsConstructedGenericType || serviceType.GetGenericTypeDefinition() != typeof(IEnumerable<>))
        {
            return null;
        }

        var elementType = serviceType.GenericTypeArguments[0];
        var inner = chain.Enter(serviceType);
        var elements = new List<(int Slot, CallSite Site)>();

        if (_slotsByServiceType.TryGetValue(elementType, out var exact))
        {
            elements.AddRange(exact.Select(slot =>
                (slot, GetSlotCallSite(_descriptors[slot], slot, elementType, inner))));
        }

        if (elementType.IsConstructedGenericType
            && _slotsByServiceType.TryGetValue(elementType.GetGenericTypeDefinition(), out var open))
        {
            foreach (var slot in open)
            {
                if (TryCloseGeneric(slot, elementType, inner) is { } site)
                {
                    elements.Add((slot, site));
                }
            }
        }

        // An empty sequence is a valid answer: "all handlers of T" may legitimately be none.
        var ordered = elements.OrderBy(e => e.Slot).Select(e => e.Site).ToList();
        return new EnumerableCallSite(serviceType, elementType, ordered);
    }

    private CallSite GetSlotCallSite(ServiceDescriptor descriptor, int slot, Type serviceType, ResolutionChain chain)
    {
        var key = new ServiceCacheKey(serviceType, slot);
        if (_slotCache.TryGetValue(key, out var cached))
        {
            return cached;
        }

        CallSite site;
        if (descriptor.Instance is not null)
        {
            site = new InstanceCallSite(serviceType, key, descriptor.Instance);
        }
        else if (descriptor.Factory is not null)
        {
            site = new FactoryCallSite(serviceType, descriptor.Lifetime, key, descriptor.Factory);
        }
        else
        {
            site = CreateConstructorSite(
                serviceType, descriptor.Lifetime, key, descriptor.ImplementationType!, chain.Enter(serviceType));
        }

        return _slotCache.GetOrAdd(key, site);
    }

    private ConstructorCallSite CreateConstructorSite(
        Type serviceType, ServiceLifetime lifetime, ServiceCacheKey key, Type implementationType, ResolutionChain chain)
    {
        var constructor = SelectConstructor(implementationType, chain);
        var parameters = constructor.GetParameters()
            .Select(p => GetCallSite(p.ParameterType, chain) ?? DefaultFor(p, implementationType, chain))
            .ToList();

        var site = new ConstructorCallSite(serviceType, lifetime, key, constructor, parameters);
        if (_validateScopes && lifetime == ServiceLifetime.Singleton && site.ScopedDependency is { } scoped)
        {
            throw new ScopeValidationException(
                $"Singleton '{TypeNames.Pretty(serviceType)}' cannot depend on scoped service " +
                $"'{TypeNames.Pretty(scoped)}': the singleton would capture the first scope's instance forever.");
        }

        return site;
    }

    /// <summary>
    /// Greedy selection: the public constructor with the most parameters that can all be
    /// satisfied. Two satisfiable constructors of equal length are ambiguous and rejected
    /// rather than picked arbitrarily.
    /// </summary>
    private ConstructorInfo SelectConstructor(Type implementationType, ResolutionChain chain)
    {
        var groups = implementationType.GetConstructors(BindingFlags.Public | BindingFlags.Instance)
            .GroupBy(c => c.GetParameters().Length)
            .OrderByDescending(g => g.Key)
            .ToList();

        if (groups.Count == 0)
        {
            throw new ContainerException($"'{TypeNames.Pretty(implementationType)}' has no public constructor.");
        }

        foreach (var group in groups)
        {
            var satisfiable = group
                .Where(c => c.GetParameters().All(p => IsResolvable(p.ParameterType) || p.HasDefaultValue))
                .ToList();

            if (satisfiable.Count > 1)
            {
                throw new ContainerException(
                    $"Ambiguous constructors on '{TypeNames.Pretty(implementationType)}': " +
                    $"{satisfiable.Count} constructors with {group.Key} resolvable parameters.");
            }

            if (satisfiable.Count == 1)
            {
                return satisfiable[0];
            }
        }

        // Report the first gap in the most specific constructor: that's the one the author meant.
        var missing = groups[0].First().GetParameters()
            .First(p => !IsResolvable(p.ParameterType) && !p.HasDefaultValue);
        throw Unresolvable(missing, implementationType, chain);
    }

    private static DefaultValueCallSite DefaultFor(ParameterInfo parameter, Type implementationType, ResolutionChain chain) =>
        parameter.HasDefaultValue
            ? new DefaultValueCallSite(parameter.ParameterType, parameter.DefaultValue)
            : throw Unresolvable(parameter, implementationType, chain); // e.g. open generic whose constraints fail

    private static UnresolvableServiceException Unresolvable(
        ParameterInfo parameter, Type implementationType, ResolutionChain chain) =>
        new(parameter.ParameterType,
            $"Unable to resolve '{TypeNames.Pretty(parameter.ParameterType)}' for parameter '{parameter.Name}' " +
            $"of '{TypeNames.Pretty(implementationType)}'. Resolution path: {chain.Describe()}.");
}
