using MiniIoC.CallSites;

namespace MiniIoC;

/// <summary>
/// The built, immutable container. Acts as the root provider (singletons live here) and
/// as the factory for child scopes. Create one with <see cref="ServiceCollection.BuildServiceProvider"/>.
/// </summary>
public sealed class Container : IServiceProvider, IServiceScopeFactory, IDisposable, IAsyncDisposable
{
    private readonly CallSiteFactory _callSites;
    private readonly ServiceScope _root;

    internal Container(ServiceDescriptor[] descriptors, ContainerOptions options)
    {
        Options = options;
        _callSites = new CallSiteFactory(descriptors, options.ValidateScopes);
        _root = new ServiceScope(this, root: null);

        if (options.ValidateOnBuild)
        {
            var errors = _callSites.ValidateAll();
            if (errors.Count > 0)
            {
                throw new ContainerValidationException(errors);
            }
        }
    }

    internal ContainerOptions Options { get; }

    /// <inheritdoc />
    public object? GetService(Type serviceType) => _root.GetService(serviceType);

    /// <inheritdoc />
    public IServiceScope CreateScope()
    {
        // Resolving through the root surfaces ObjectDisposedException once the container is gone.
        _ = _root.GetService(typeof(IServiceScopeFactory));
        return new ServiceScope(this, _root);
    }

    /// <summary>Disposes every singleton and root-owned transient.</summary>
    public void Dispose() => _root.Dispose();

    /// <inheritdoc />
    public ValueTask DisposeAsync() => _root.DisposeAsync();

    internal object? Resolve(Type serviceType, ServiceScope scope)
    {
        var site = _callSites.GetCallSite(serviceType);
        return site is null ? null : CallSiteResolver.Resolve(site, scope);
    }
}
