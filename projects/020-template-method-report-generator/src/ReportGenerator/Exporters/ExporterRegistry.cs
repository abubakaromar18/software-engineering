namespace ReportGenerator.Exporters;

/// <summary>
/// Looks exporters up by format name. Adding a format means writing one subclass
/// and registering it here; nothing else changes (Open/Closed).
/// </summary>
public sealed class ExporterRegistry
{
    private readonly Dictionary<string, Func<ReportExporter>> _factories = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>A registry preloaded with the built-in CSV, JSON and HTML exporters.</summary>
    public static ExporterRegistry CreateDefault() =>
        new ExporterRegistry()
            .Register("csv", () => new CsvExporter())
            .Register("json", () => new JsonExporter())
            .Register("html", () => new HtmlExporter());

    public IEnumerable<string> Formats => _factories.Keys.Order(StringComparer.Ordinal);

    public ExporterRegistry Register(string format, Func<ReportExporter> factory)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(format);
        ArgumentNullException.ThrowIfNull(factory);
        if (!_factories.TryAdd(format, factory))
        {
            throw new InvalidOperationException($"Format '{format}' is already registered.");
        }

        return this;
    }

    public ReportExporter Create(string format) =>
        _factories.TryGetValue(format, out var factory)
            ? factory()
            : throw new UnknownFormatException(format, Formats);
}

/// <summary>Raised when no exporter is registered for a format.</summary>
public sealed class UnknownFormatException(string format, IEnumerable<string> known)
    : Exception($"Unknown format '{format}'. Known formats: {string.Join(", ", known)}.")
{
    public string Format { get; } = format;
}
