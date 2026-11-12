namespace ReportGenerator.Exporters;

/// <summary>Caller-level switches. Formats see these through their hooks and may refine them.</summary>
public sealed record ExportOptions(bool IncludeTitle = true, bool IncludeSummary = true)
{
    public static ExportOptions Default { get; } = new();
}
