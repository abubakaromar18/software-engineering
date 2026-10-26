namespace MiniIoC;

/// <summary>Controls how long a resolved instance lives and who shares it.</summary>
public enum ServiceLifetime
{
    /// <summary>One instance for the whole container, created lazily and disposed with the container.</summary>
    Singleton,

    /// <summary>One instance per <see cref="IServiceScope"/>, disposed when that scope is disposed.</summary>
    Scoped,

    /// <summary>A new instance on every resolution; disposables are tracked by the resolving scope.</summary>
    Transient,
}
