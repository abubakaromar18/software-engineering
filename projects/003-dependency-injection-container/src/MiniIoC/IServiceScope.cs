namespace MiniIoC;

/// <summary>
/// A unit of work (e.g. one web request) that owns its scoped instances and the
/// disposable transients resolved through it.
/// </summary>
public interface IServiceScope : IDisposable, IAsyncDisposable
{
    /// <summary>The provider that resolves services within this scope.</summary>
    IServiceProvider ServiceProvider { get; }
}

/// <summary>Creates new scopes. Resolvable from any provider built by this library.</summary>
public interface IServiceScopeFactory
{
    /// <summary>Creates a new, independent scope.</summary>
    IServiceScope CreateScope();
}
