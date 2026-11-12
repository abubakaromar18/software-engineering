using ReportGenerator.Model;

namespace ReportGenerator.Exporters;

/// <summary>
/// RFC 4180 CSV. CSV is a data-interchange format, so it overrides both hooks to
/// say "never": a title line or a totals row would break every downstream parser.
/// </summary>
public sealed class CsvExporter : ReportExporter
{
    private static readonly char[] CharactersRequiringQuotes = [',', '"', '\r', '\n'];

    public override string FormatName => "csv";

    public override string FileExtension => ".csv";

    protected override bool ShouldWriteTitle(ExportOptions options) => false;

    protected override bool ShouldWriteSummary(ExportOptions options) => false;

    protected override void BeginDocument(Report report, TextWriter writer)
    {
        // CSV has no document wrapper.
    }

    protected override void WriteHeader(IReadOnlyList<Column> columns, TextWriter writer) =>
        WriteLine(columns.Select(c => c.Name), writer);

    protected override void WriteRow(IReadOnlyList<Column> columns, IReadOnlyList<object?> row, int rowIndex, TextWriter writer) =>
        WriteLine(row.Select((value, i) => FormatValue(value, columns[i])), writer);

    protected override void EndDocument(Report report, TextWriter writer)
    {
        // Nothing to close.
    }

    private static void WriteLine(IEnumerable<string> fields, TextWriter writer)
    {
        writer.Write(string.Join(',', fields.Select(Escape)));
        writer.Write("\r\n"); // RFC 4180 mandates CRLF regardless of platform
    }

    /// <summary>Quotes a field only when needed and doubles embedded quotes.</summary>
    public static string Escape(string field) =>
        field.IndexOfAny(CharactersRequiringQuotes) >= 0
            ? $"\"{field.Replace("\"", "\"\"", StringComparison.Ordinal)}\""
            : field;
}
