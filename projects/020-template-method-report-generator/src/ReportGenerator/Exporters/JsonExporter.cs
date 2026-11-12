using System.Globalization;
using System.Text.Encodings.Web;
using System.Text.Json;
using ReportGenerator.Model;

namespace ReportGenerator.Exporters;

/// <summary>
/// JSON document of the shape
/// <c>{ "title": ..., "columns": [...], "rows": [ {..}, .. ], "summary": {..} }</c>.
/// Numbers stay JSON numbers and missing cells become <c>null</c>, so the string
/// <see cref="ReportExporter.FormatValue"/> is only used for text and dates.
/// <para>
/// Streaming JSON by hand means knowing where commas go; that is why the template
/// passes <c>rowIndex</c> to <see cref="WriteRow"/> and the row count to
/// <see cref="EndRows"/>. The exporter keeps no state between calls.
/// </para>
/// </summary>
public sealed class JsonExporter : ReportExporter
{
    private const string Indent = "  ";

    // Relaxed escaping keeps quotes and non-ASCII readable ("\"Pro\"" rather than "\u0022Pro\u0022").
    // It is safe for a standalone .json file; it would not be for JSON inlined into HTML <script>.
    private static readonly JsonSerializerOptions StringOptions = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };

    public override string FormatName => "json";

    public override string FileExtension => ".json";

    protected override void BeginDocument(Report report, TextWriter writer) => writer.Write('{');

    protected override void WriteTitle(string title, TextWriter writer) =>
        writer.Write($"\n{Indent}\"title\": {Quote(title)},");

    protected override void WriteHeader(IReadOnlyList<Column> columns, TextWriter writer)
    {
        var described = columns.Select(c =>
            $"{{ \"name\": {Quote(c.Name)}, \"type\": {Quote(c.Type.ToString().ToLowerInvariant())} }}");
        writer.Write($"\n{Indent}\"columns\": [\n{Indent}{Indent}");
        writer.Write(string.Join($",\n{Indent}{Indent}", described));
        writer.Write($"\n{Indent}],");
    }

    protected override void BeginRows(TextWriter writer) => writer.Write($"\n{Indent}\"rows\": [");

    protected override void WriteRow(IReadOnlyList<Column> columns, IReadOnlyList<object?> row, int rowIndex, TextWriter writer)
    {
        var fields = row.Select((value, i) => $"{Quote(columns[i].Name)}: {Literal(value, columns[i])}");
        writer.Write(rowIndex == 0 ? "\n" : ",\n");
        writer.Write($"{Indent}{Indent}{{ {string.Join(", ", fields)} }}");
    }

    protected override void EndRows(int rowCount, TextWriter writer) =>
        writer.Write(rowCount == 0 ? "]" : $"\n{Indent}]");

    protected override void WriteSummary(IReadOnlyList<Column> columns, ReportSummary summary, TextWriter writer)
    {
        var totals = columns
            .Where(c => c.Type.IsNumeric())
            .Select(c => $"{Quote(c.Name)}: {Number(summary.TotalFor(c) ?? 0m)}");
        writer.Write($",\n{Indent}\"summary\": {{ \"rowCount\": {summary.RowCount}, \"totals\": {{ {string.Join(", ", totals)} }} }}");
    }

    protected override void EndDocument(Report report, TextWriter writer) => writer.Write("\n}\n");

    private string Literal(object? value, Column column) => value switch
    {
        null => "null",
        long l => l.ToString(CultureInfo.InvariantCulture),
        decimal d => Number(d),
        _ => Quote(FormatValue(value, column)),
    };

    private static string Number(decimal value) => value.ToString(CultureInfo.InvariantCulture);

    /// <summary>JSON string literal with correct escaping (quotes, control characters, non-ASCII).</summary>
    private static string Quote(string text) => JsonSerializer.Serialize(text, StringOptions);
}
