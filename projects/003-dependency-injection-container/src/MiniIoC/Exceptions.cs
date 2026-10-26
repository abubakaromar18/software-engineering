namespace MiniIoC;

/// <summary>Base type for every error raised by the container.</summary>
public class ContainerException : Exception
{
    /// <inheritdoc />
    public ContainerException(string message) : base(message) { }

    /// <inheritdoc />
    public ContainerException(string message, Exception inner) : base(message, inner) { }
}

/// <summary>A service (directly or transitively) depends on itself.</summary>
public sealed class CircularDependencyException : ContainerException
{
    /// <summary>Creates the exception from the offending dependency path.</summary>
    public CircularDependencyException(IReadOnlyList<Type> path)
        : base($"Circular dependency detected: {string.Join(" -> ", path.Select(TypeNames.Pretty))}.")
    {
        Path = path;
    }

    /// <summary>The cycle, starting and ending with the same service type.</summary>
    public IReadOnlyList<Type> Path { get; }
}

/// <summary>A required service or constructor parameter has no registration.</summary>
public sealed class UnresolvableServiceException : ContainerException
{
    /// <summary>Creates the exception for <paramref name="serviceType"/>.</summary>
    public UnresolvableServiceException(Type serviceType, string message) : base(message)
    {
        ServiceType = serviceType;
    }

    /// <summary>The type that could not be resolved.</summary>
    public Type ServiceType { get; }
}

/// <summary>A lifetime rule was broken (captive dependency or scoped service resolved from the root).</summary>
public sealed class ScopeValidationException : ContainerException
{
    /// <inheritdoc />
    public ScopeValidationException(string message) : base(message) { }
}

/// <summary>Raised by <see cref="ContainerOptions.ValidateOnBuild"/> with every problem found.</summary>
public sealed class ContainerValidationException : ContainerException
{
    /// <summary>Creates the exception from the individual validation errors.</summary>
    public ContainerValidationException(IReadOnlyList<ContainerException> errors)
        : base("Container validation failed:" + Environment.NewLine +
               string.Join(Environment.NewLine, errors.Select(e => "  - " + e.Message)))
    {
        Errors = errors;
    }

    /// <summary>The individual errors, one per failing registration.</summary>
    public IReadOnlyList<ContainerException> Errors { get; }
}
