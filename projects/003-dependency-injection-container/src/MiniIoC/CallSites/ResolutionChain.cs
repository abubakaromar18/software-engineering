namespace MiniIoC.CallSites;

/// <summary>
/// The immutable stack of service types currently being planned. Each recursive step
/// pushes a new node, so sibling branches never see each other's entries and no cleanup
/// is needed when a branch finishes or throws.
/// </summary>
internal sealed class ResolutionChain
{
    private readonly Type? _type;
    private readonly ResolutionChain? _parent;

    private ResolutionChain(Type? type, ResolutionChain? parent)
    {
        _type = type;
        _parent = parent;
    }

    public static ResolutionChain Empty { get; } = new(null, null);

    /// <summary>Returns a chain extended with <paramref name="serviceType"/>.</summary>
    /// <exception cref="CircularDependencyException">The type is already being planned.</exception>
    public ResolutionChain Enter(Type serviceType)
    {
        if (Contains(serviceType))
        {
            var path = ToList().SkipWhile(t => t != serviceType).Append(serviceType).ToList();
            throw new CircularDependencyException(path);
        }

        return new ResolutionChain(serviceType, this);
    }

    /// <summary>Human-readable path from the outermost request to the current node.</summary>
    public string Describe() =>
        _type is null ? "(root)" : string.Join(" -> ", ToList().Select(TypeNames.Pretty));

    private bool Contains(Type serviceType)
    {
        for (var node = this; node?._type is not null; node = node._parent)
        {
            if (node._type == serviceType)
            {
                return true;
            }
        }

        return false;
    }

    private List<Type> ToList()
    {
        var types = new List<Type>();
        for (var node = this; node?._type is not null; node = node._parent)
        {
            types.Add(node._type);
        }

        types.Reverse();
        return types;
    }
}
