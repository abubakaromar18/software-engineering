using System.Collections;

namespace MiniIoC;

/// <summary>
/// The mutable registration phase. Registrations are append-only and ordered: the last
/// registration for a service type wins for single resolution, while
/// <see cref="IEnumerable{T}"/> resolves all of them in registration order.
/// </summary>
public sealed class ServiceCollection : IReadOnlyList<ServiceDescriptor>
{
    private readonly List<ServiceDescriptor> _descriptors = [];

    /// <inheritdoc />
    public int Count => _descriptors.Count;

    /// <inheritdoc />
    public ServiceDescriptor this[int index] => _descriptors[index];

    /// <summary>Appends a registration.</summary>
    public ServiceCollection Add(ServiceDescriptor descriptor)
    {
        ArgumentNullException.ThrowIfNull(descriptor);
        _descriptors.Add(descriptor);
        return this;
    }

    /// <summary>Appends the registration only if the service type is not registered yet.</summary>
    /// <returns><c>true</c> if the descriptor was added.</returns>
    public bool TryAdd(ServiceDescriptor descriptor)
    {
        ArgumentNullException.ThrowIfNull(descriptor);
        if (_descriptors.Exists(d => d.ServiceType == descriptor.ServiceType))
        {
            return false;
        }

        _descriptors.Add(descriptor);
        return true;
    }

    /// <summary>
    /// Freezes the registrations into a container. Later changes to this collection do
    /// not affect containers already built.
    /// </summary>
    public Container BuildServiceProvider(ContainerOptions? options = null) =>
        new(_descriptors.ToArray(), options ?? ContainerOptions.Default);

    /// <inheritdoc />
    public IEnumerator<ServiceDescriptor> GetEnumerator() => _descriptors.GetEnumerator();

    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();
}
