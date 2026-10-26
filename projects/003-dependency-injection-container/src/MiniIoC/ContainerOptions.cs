namespace MiniIoC;

/// <summary>Build-time switches for a <see cref="Container"/>.</summary>
public sealed record ContainerOptions
{
    /// <summary>
    /// Reject singletons that (transitively) capture scoped services and reject resolving
    /// scoped services from the root provider. Defaults to <c>true</c>: the checks are cheap
    /// because they run once per call site, and captive dependencies are a classic,
    /// hard-to-debug lifetime bug.
    /// </summary>
    public bool ValidateScopes { get; init; } = true;

    /// <summary>
    /// Build the call site of every registration when the container is created so that
    /// missing dependencies and cycles fail at startup rather than on first use.
    /// </summary>
    public bool ValidateOnBuild { get; init; } = true;

    /// <summary>The default options.</summary>
    public static ContainerOptions Default { get; } = new();
}
