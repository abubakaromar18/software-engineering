using System.Text.Json;
using ReportGenerator.Exporters;
using Xunit;

namespace ReportGenerator.Tests;

public class JsonExporterTests
{
    private static JsonElement Parse(string json) => JsonDocument.Parse(json).RootElement;

    [Fact]
    public void Produces_valid_json_with_typed_values()
    {
        var root = Parse(TestData.Render(new JsonExporter(), TestData.Sales()));

        Assert.Equal("Q3 Sales", root.GetProperty("title").GetString());
        Assert.Equal("integer", root.GetProperty("columns")[1].GetProperty("type").GetString());

        var south = root.GetProperty("rows")[1];
        Assert.Equal("South, East", south.GetProperty("Region").GetString());
        Assert.Equal(JsonValueKind.Number, south.GetProperty("Units").ValueKind);
        Assert.Equal(6705.50m, south.GetProperty("Revenue").GetDecimal());
        Assert.Equal(JsonValueKind.Null, south.GetProperty("Shipped").ValueKind);
        Assert.Equal("2026-09-28", root.GetProperty("rows")[2].GetProperty("Shipped").GetString());
        Assert.Equal("West \"HQ\"", root.GetProperty("rows")[2].GetProperty("Region").GetString());
    }

    [Fact]
    public void Summary_totals_numeric_columns_only()
    {
        var summary = Parse(TestData.Render(new JsonExporter(), TestData.Sales())).GetProperty("summary");

        Assert.Equal(3, summary.GetProperty("rowCount").GetInt32());
        var totals = summary.GetProperty("totals");
        Assert.Equal(2225m, totals.GetProperty("Units").GetDecimal());
        Assert.Equal(31695.70m, totals.GetProperty("Revenue").GetDecimal());
        Assert.False(totals.TryGetProperty("Region", out _));
    }

    [Theory]
    [InlineData(true, true)]
    [InlineData(true, false)]
    [InlineData(false, true)]
    [InlineData(false, false)]
    public void Every_option_combination_is_valid_json(bool title, bool summary)
    {
        var options = new ExportOptions(title, summary);

        foreach (var report in new[] { TestData.Sales(), TestData.Empty() })
        {
            var root = Parse(TestData.Render(new JsonExporter(), report, options));
            Assert.Equal(title, root.TryGetProperty("title", out _));
            Assert.Equal(summary, root.TryGetProperty("summary", out _));
            Assert.Equal(report.Rows.Count, root.GetProperty("rows").GetArrayLength());
        }
    }

    [Fact]
    public void The_same_instance_can_export_repeatedly()
    {
        var exporter = new JsonExporter();

        var first = TestData.Render(exporter, TestData.Sales());
        var second = TestData.Render(exporter, TestData.Sales());

        Assert.Equal(first, second);
    }
}
