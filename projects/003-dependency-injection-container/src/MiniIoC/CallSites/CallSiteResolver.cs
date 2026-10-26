using System.Reflection;
using System.Runtime.ExceptionServices;

namespace MiniIoC.CallSites;

/// <summary>
/// Executes a call site against a scope: applies lifetime caching, activates instances
/// and hands disposables to the owning scope. Stateless apart from the factory guard.
/// </summary>
internal static class CallSiteResolver
{
    // Factories are opaque at plan time, so a factory that (indirectly) resolves its own
    // service can only be caught while it runs. Tracked per thread because one resolution
    // graph always executes on a single thread.
    [ThreadStatic]
    private static HashSet<ServiceCacheKey>? s_activeFactories;

    public static object? Resolve(CallSite site, ServiceScope scope)
    {
        switch (site)
        {
            case InstanceCallSite instance:
                return instance.Instance; // caller-owned: never cached, never disposed
            case ServiceProviderCallSite:
                return scope;
            case ScopeFactoryCallSite:
                return scope.Container;
            case DefaultValueCallSite defaultValue:
                return defaultValue.Value;
        }

        return site.Lifetime switch
        {
            // Singletons are activated by the root so their own dependencies (and any
            // disposable transients they pull in) are owned by the root, not by whichever
            // short-lived scope happened to ask first.
            ServiceLifetime.Singleton => scope.Root.GetOrCreate(site, () => Activate(site, scope.Root)),
            ServiceLifetime.Scoped => ResolveScoped(site, scope),
            _ => scope.Track(Activate(site, scope)),
        };
    }

    private static object ResolveScoped(CallSite site, ServiceScope scope)
    {
        if (scope.IsRoot && scope.Container.Options.ValidateScopes)
        {
            throw new ScopeValidationException(
                $"Cannot resolve scoped service '{TypeNames.Pretty(site.ServiceType)}' from the root provider. " +
                "Create a scope first.");
        }

        return scope.GetOrCreate(site, () => Activate(site, scope));
    }

    private static object Activate(CallSite site, ServiceScope scope) => site switch
    {
        ConstructorCallSite ctor => Construct(ctor, scope),
        FactoryCallSite factory => InvokeFactory(factory, scope),
        EnumerableCallSite enumerable => BuildArray(enumerable, scope),
        _ => throw new InvalidOperationException($"Unknown call site '{site.GetType().Name}'."),
    };

    private static object Construct(ConstructorCallSite site, ServiceScope scope)
    {
        var args = new object?[site.Dependencies.Count];
        for (var i = 0; i < args.Length; i++)
        {
            args[i] = Resolve(site.Dependencies[i], scope);
        }

        try
        {
            return site.Constructor.Invoke(args);
        }
        catch (TargetInvocationException ex) when (ex.InnerException is not null)
        {
            // Surface the constructor's own exception, not the reflection wrapper.
            ExceptionDispatchInfo.Capture(ex.InnerException).Throw();
            throw; // unreachable
        }
    }

    private static object InvokeFactory(FactoryCallSite site, ServiceScope scope)
    {
        var active = s_activeFactories ??= [];
        if (!active.Add(site.CacheKey))
        {
            throw new CircularDependencyException([site.ServiceType, site.ServiceType]);
        }

        try
        {
            return site.Factory(scope)
                   ?? throw new ContainerException(
                       $"The factory for '{TypeNames.Pretty(site.ServiceType)}' returned null.");
        }
        finally
        {
            active.Remove(site.CacheKey);
        }
    }

    private static Array BuildArray(EnumerableCallSite site, ServiceScope scope)
    {
        var array = Array.CreateInstance(site.ElementType, site.Dependencies.Count);
        for (var i = 0; i < array.Length; i++)
        {
            array.SetValue(Resolve(site.Dependencies[i], scope), i);
        }

        return array;
    }
}
