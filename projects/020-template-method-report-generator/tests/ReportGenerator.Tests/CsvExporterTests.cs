using ReportGenerator.Exporters;
using ReportGenerator.Input;
using Xunit;

namespace ReportGenerator.Tests;

public class CsvExporterTests
{
    [Theory]
    [InlineData("plain", "plain")]
    [InlineData("a,b", "\"a,b\"")]
    [InlineData("say \"hi\"", "\"say \"\"hi\"\"\"")]
    [InlineData("two\nlines", "\"two\nlines\"")]
    [InlineData("", "")]
    public void Escape_quotes_only_when_rfc4180_requires_it(string field, string expected)
    {
        Assert.Equal(expected, CsvExporter.Escape(field));
    }

    [Fact]
    public void Writes_header_and_rows_with_crlf_and_invariant_values()
    {
        var csv = TestData.Render(new CsvExporter(), TestData.Sales());

        Assert.Equal(
            "Region,Units,Revenue,Shipped\r\n" +
            "North,1200,5400.00,2026-07-03\r\n" +
            "\"South, East\",45,6705.50,\r\n" +
            "\"West \"\"HQ\"\"\",980,19590.20,2026-09-28\r\n",
            csv);
    }

    [Fact]
    public void Hooks_suppress_title_and_summary_even_when_requested()
    {
        var csv = TestData.Render(new CsvExporter(), TestData.Sales(), new ExportOptions(IncludeTitle: true, IncludeSummary: true));

        Assert.DoesNotContain("Q3 Sales", csv);
        Assert.DoesNotContain("25695.70", csv);
    }

    [Fact]
    public void Output_round_trips_through_the_loader()
    {
        var original = TestData.Sales();

        var reloaded = ReportLoader.FromCsv(original.Title, new StringReader(TestData.Render(new CsvExporter(), original)));

        Assert.Equal(original.Columns, reloaded.Columns);
        for (var i = 0; i < original.Rows.Count; i++)
        {
            Assert.Equal(original.Rows[i], reloaded.Rows[i]);
        }
    }
}
