using System.Runtime.ExceptionServices;
using MiniIoC.CallSites;

namespace MiniIoC;

/// <summary>
/// Owns the instances cached for one lifetime boundary. The container's root scope holds
/// singletons; every <see cref="Container.CreateScope"/> call creates a child that holds
/// scoped instances. Each scope disposes what it owns in reverse creation order.
/// </summary>
public sealed class ServiceScope : IServiceScope, IServiceProvider
{
    private readonly Dictionary<ServiceCacheKey, object> _instances = [];
    private readonly List<object> _disposables = [];

    // One re-entrant lock per scope. Creating an instance happens under the lock so each
    // cached service is constructed exactly once. Lock order is always child -> root
    // (singletons never touch a child scope), so nested resolution cannot deadlock.
    private readonly object _sync = new();
    private bool _disposed;

    internal ServiceScope(Container container, ServiceScope? root)
    {
        Container = container;
        Root = root ?? this;
    }

    /// <inheritdoc />
    public IServiceProvider ServiceProvider => this;

    internal Container Container { get; }

    internal ServiceScope Root { get; }

    internal bool IsRoot => ReferenceEquals(Root, this);

    /// <inheritdoc />
    public object? GetService(Type serviceType)
    {
        ArgumentNullException.ThrowIfNull(serviceType);
        ThrowIfDisposed();
        return Container.Resolve(serviceType, this);
    }

    internal object GetOrCreate(CallSite site, Func<object> create)
    {
        lock (_sync)
        {
            ThrowIfDisposed();
            if (_instances.TryGetValue(site.CacheKey, out var existing))
            {
                return existing;
            }

            var instance = create();
            _instances[site.CacheKey] = instance;
            Track(instance);
            return instance;
        }
    }

    /// <summary>Takes ownership of <paramref name="instance"/> if it needs disposing.</summary>
    internal object Track(object instance)
    {
        if (instance is not (IDisposable or IAsyncDisposable))
        {
            return instance;
        }

        lock (_sync)
        {
            if (!_disposed)
            {
                _disposables.Add(instance);
                return instance;
            }
        }

        // Lost a race with Dispose: don't leak the instance we just built.
        (instance as IDisposable)?.Dispose();
        throw new ObjectDisposedException(nameof(ServiceScope));
    }

    /// <summary>Disposes owned instances in reverse creation order.</summary>
    /// <remarks>
    /// Every instance is attempted even if an earlier one throws. A single failure is
    /// rethrown as-is; several are wrapped in an <see cref="AggregateException"/>.
    /// </remarks>
    /// <exception cref="InvalidOperationException">An owned instance only supports async disposal.</exception>
    public void Dispose()
    {
        var owned = BeginDispose();
        var errors = new List<Exception>();
        foreach (var instance in owned)
        {
            try
            {
                switch (instance)
                {
                    case IDisposable disposable:
                        disposable.Dispose();
                        break;
                    case IAsyncDisposable:
                        throw new InvalidOperationException(
                            $"'{TypeNames.Pretty(instance.GetType())}' only implements IAsyncDisposable. " +
                            "Use DisposeAsync to dispose this scope.");
                }
            }
            catch (Exception ex)
            {
                errors.Add(ex); // keep going: one bad Dispose must not leak the rest
            }
        }

        ThrowIfAny(errors);
    }

    /// <summary>Asynchronously disposes owned instances in reverse creation order.</summary>
    public async ValueTask DisposeAsync()
    {
        var owned = BeginDispose();
        var errors = new List<Exception>();
        foreach (var instance in owned)
        {
            try
            {
                if (instance is IAsyncDisposable asyncDisposable)
                {
                    await asyncDisposable.DisposeAsync().ConfigureAwait(false);
                }
                else
                {
                    ((IDisposable)instance).Dispose();
                }
            }
            catch (Exception ex)
            {
                errors.Add(ex);
            }
        }

        ThrowIfAny(errors);
    }

    private List<object> BeginDispose()
    {
        lock (_sync)
        {
            if (_disposed)
            {
                return [];
            }

            _disposed = true;
            var owned = new List<object>(_disposables);
            owned.Reverse();
            _disposables.Clear();
            _instances.Clear();
            return owned;
        }
    }

    private void ThrowIfDisposed() => ObjectDisposedException.ThrowIf(_disposed, this);

    private static void ThrowIfAny(List<Exception> errors)
    {
        switch (errors.Count)
        {
            case 0:
                return;
            case 1:
                ExceptionDispatchInfo.Capture(errors[0]).Throw(); // keep the original type and stack
                return;
            default:
                throw new AggregateException("One or more services failed to dispose.", errors);
        }
    }
}
