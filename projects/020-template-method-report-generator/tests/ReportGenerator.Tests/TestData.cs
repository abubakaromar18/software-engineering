using ReportGenerator.Model;

namespace ReportGenerator.Tests;

/// <summary>Shared fixtures. Each call returns a fresh report.</summary>
internal static class TestData
{
    public static Report Sales(string title = "Q3 Sales") => new(
        title,
        [
            new Column("Region", ColumnType.Text),
            new Column("Units", ColumnType.Integer),
            new Column("Revenue", ColumnType.Decimal),
            new Column("Shipped", ColumnType.Date),
        ],
        [
            Row("North", 1200L, 5400.00m, new DateOnly(2026, 7, 3)),
            Row("South, East", 45L, 6705.50m, null),
            Row("West \"HQ\"", 980L, 19590.20m, new DateOnly(2026, 9, 28)),
        ]);

    public static Report Empty() => new("Nothing", [new Column("Name", ColumnType.Text)], []);

    public static IReadOnlyList<object?> Row(params object?[] cells) => cells;

    public static string Render(Exporters.ReportExporter exporter, Report report, Exporters.ExportOptions? options = null)
    {
        using var writer = new StringWriter();
        exporter.Export(report, writer, options);
        return writer.ToString();
    }
}
