namespace CatalogProxies.Lazy;

/// <summary>
/// Thread-safe asynchronous lazy initialisation.
/// <para>
/// Unlike <c>new Lazy&lt;Task&lt;T&gt;&gt;(...)</c>, a failed or cancelled initialisation is
/// <b>not</b> cached: the next caller starts a fresh attempt. That suits resources like
/// connections, where a transient failure shouldn't poison the object for its whole life.
/// </para>
/// <para>
/// The factory runs at most once at a time. Concurrent callers share the attempt in flight.
/// A caller's <see cref="CancellationToken"/> only stops that caller waiting; it never cancels
/// the shared attempt, because other callers may still want the result.
/// </para>
/// </summary>
public sealed class AsyncLazy<T>
{
    private readonly Func<CancellationToken, Task<T>> _factory;
    private readonly object _gate = new();
    private Task<T>? _attempt;

    public AsyncLazy(Func<CancellationToken, Task<T>> factory)
    {
        ArgumentNullException.ThrowIfNull(factory);
        _factory = factory;
    }

    /// <summary>True once the factory has completed successfully.</summary>
    public bool IsValueCreated
    {
        get
        {
            lock (_gate)
            {
                return _attempt is { IsCompletedSuccessfully: true };
            }
        }
    }

    /// <summary>True when an attempt has been started and has not failed.</summary>
    public bool IsStarted
    {
        get
        {
            lock (_gate)
            {
                return _attempt is { IsFaulted: false, IsCanceled: false };
            }
        }
    }

    public Task<T> GetValueAsync(CancellationToken cancellationToken = default) =>
        CurrentAttempt().WaitAsync(cancellationToken);

    /// <summary>Returns the value if it has already been created, without starting the factory.</summary>
    public bool TryGetValue(out T value)
    {
        lock (_gate)
        {
            if (_attempt is { IsCompletedSuccessfully: true } done)
            {
                value = done.Result;
                return true;
            }
        }

        value = default!;
        return false;
    }

    private Task<T> CurrentAttempt()
    {
        lock (_gate)
        {
            if (_attempt is null || _attempt.IsFaulted || _attempt.IsCanceled)
            {
                // Task.Run keeps a synchronous factory from running while we hold the lock,
                // and from running on the caller's synchronization context.
                _attempt = Task.Run(() => _factory(CancellationToken.None));
            }

            return _attempt;
        }
    }
}
