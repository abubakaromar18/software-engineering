namespace ReportGenerator.Model;

/// <summary>A named, typed column of a <see cref="Report"/>.</summary>
public sealed record Column
{
    public Column(string name, ColumnType type)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        Name = name.Trim();
        Type = type;
    }

    public string Name { get; }

    public ColumnType Type { get; }
}
