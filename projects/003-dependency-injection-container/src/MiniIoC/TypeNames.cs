namespace MiniIoC;

/// <summary>Formats types the way they are written in C# (e.g. <c>IRepository&lt;User&gt;</c>).</summary>
internal static class TypeNames
{
    public static string Pretty(Type type)
    {
        if (!type.IsGenericType)
        {
            return type.Name;
        }

        var name = type.Name[..type.Name.IndexOf('`', StringComparison.Ordinal)];
        var args = type.IsGenericTypeDefinition
            ? string.Join(",", type.GetGenericArguments().Select(_ => string.Empty))
            : string.Join(", ", type.GetGenericArguments().Select(Pretty));
        return $"{name}<{args}>";
    }
}
