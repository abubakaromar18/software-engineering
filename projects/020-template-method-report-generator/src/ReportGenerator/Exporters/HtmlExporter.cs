using System.Globalization;
using System.Net;
using ReportGenerator.Model;

namespace ReportGenerator.Exporters;

/// <summary>
/// A standalone HTML5 page with an embedded stylesheet. HTML is a presentation
/// format, so it overrides <see cref="FormatValue"/> to group thousands and fix
/// decimals at two places, and it right-aligns numeric columns. Every piece of
/// report data is HTML-encoded: report content is untrusted input.
/// </summary>
public sealed class HtmlExporter : ReportExporter
{
    private const string Stylesheet =
        "body{font-family:system-ui,sans-serif;margin:2rem;color:#1f2328}" +
        "table{border-collapse:collapse;min-width:24rem}" +
        "th,td{border:1px solid #d0d7de;padding:.4rem .75rem;text-align:left}" +
        "th{background:#f6f8fa}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}" +
        "tfoot td{font-weight:600;background:#f6f8fa}";

    public override string FormatName => "html";

    public override string FileExtension => ".html";

    protected override void BeginDocument(Report report, TextWriter writer)
    {
        writer.WriteLine("<!DOCTYPE html>");
        writer.WriteLine("<html lang=\"en\">");
        writer.WriteLine("<head>");
        writer.WriteLine("<meta charset=\"utf-8\">");
        writer.WriteLine($"<title>{Encode(report.Title)}</title>");
        writer.WriteLine($"<style>{Stylesheet}</style>");
        writer.WriteLine("</head>");
        writer.WriteLine("<body>");
    }

    protected override void WriteTitle(string title, TextWriter writer) =>
        writer.WriteLine($"<h1>{Encode(title)}</h1>");

    protected override void WriteHeader(IReadOnlyList<Column> columns, TextWriter writer)
    {
        writer.WriteLine("<table>");
        writer.WriteLine("<thead>");
        writer.WriteLine($"<tr>{string.Concat(columns.Select(c => $"<th{NumClass(c)} scope=\"col\">{Encode(c.Name)}</th>"))}</tr>");
        writer.WriteLine("</thead>");
    }

    protected override void BeginRows(TextWriter writer) => writer.WriteLine("<tbody>");

    protected override void WriteRow(IReadOnlyList<Column> columns, IReadOnlyList<object?> row, int rowIndex, TextWriter writer)
    {
        var cells = row.Select((value, i) => $"<td{NumClass(columns[i])}>{Encode(FormatValue(value, columns[i]))}</td>");
        writer.WriteLine($"<tr>{string.Concat(cells)}</tr>");
    }

    protected override void EndRows(int rowCount, TextWriter writer) => writer.WriteLine("</tbody>");

    protected override void WriteSummary(IReadOnlyList<Column> columns, ReportSummary summary, TextWriter writer)
    {
        var cells = columns.Select((column, i) =>
        {
            var text = summary.TotalFor(column) is { } total
                ? FormatValue(column.Type == ColumnType.Integer ? (object)(long)total : total, column)
                : i == 0 ? $"Total ({summary.RowCount} rows)" : string.Empty;
            return $"<td{NumClass(column)}>{Encode(text)}</td>";
        });
        writer.WriteLine($"<tfoot><tr>{string.Concat(cells)}</tr></tfoot>");
    }

    protected override void EndDocument(Report report, TextWriter writer)
    {
        writer.WriteLine("</table>");
        writer.WriteLine("</body>");
        writer.WriteLine("</html>");
    }

    protected override string FormatValue(object? value, Column column) => value switch
    {
        long l => l.ToString("N0", CultureInfo.InvariantCulture),
        decimal d => d.ToString("N2", CultureInfo.InvariantCulture),
        DateOnly date => date.ToString("d MMM yyyy", CultureInfo.InvariantCulture),
        _ => base.FormatValue(value, column),
    };

    private static string NumClass(Column column) => column.Type.IsNumeric() ? " class=\"num\"" : string.Empty;

    private static string Encode(string text) => WebUtility.HtmlEncode(text);
}
