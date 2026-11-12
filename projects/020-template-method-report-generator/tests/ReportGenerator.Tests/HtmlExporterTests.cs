using ReportGenerator.Exporters;
using ReportGenerator.Model;
using Xunit;

namespace ReportGenerator.Tests;

public class HtmlExporterTests
{
    [Fact]
    public void Produces_a_complete_document_with_title_and_table()
    {
        var html = TestData.Render(new HtmlExporter(), TestData.Sales());

        Assert.StartsWith("<!DOCTYPE html>", html);
        Assert.Contains("<title>Q3 Sales</title>", html);
        Assert.Contains("<h1>Q3 Sales</h1>", html);
        Assert.Contains("<th class=\"num\" scope=\"col\">Units</th>", html);
        Assert.EndsWith("</html>" + Environment.NewLine, html);
    }

    [Fact]
    public void Presentation_formatting_overrides_the_default_hook()
    {
        var html = TestData.Render(new HtmlExporter(), TestData.Sales());

        Assert.Contains("<td class=\"num\">1,200</td>", html);
        Assert.Contains("<td class=\"num\">19,590.20</td>", html);
        Assert.Contains("<td>28 Sep 2026</td>", html);
    }

    [Fact]
    public void Summary_is_a_table_footer_with_integer_totals_kept_whole()
    {
        var html = TestData.Render(new HtmlExporter(), TestData.Sales());

        Assert.Contains(
            "<tfoot><tr><td>Total (3 rows)</td><td class=\"num\">2,225</td><td class=\"num\">31,695.70</td><td></td></tr></tfoot>",
            html);
        Assert.DoesNotContain("<tfoot>", TestData.Render(new HtmlExporter(), TestData.Sales(), new ExportOptions(IncludeSummary: false)));
    }

    [Fact]
    public void All_report_content_is_html_encoded()
    {
        var hostile = new Report(
            "<script>alert(1)</script>",
            [new Column("<b>Name</b>", ColumnType.Text)],
            [TestData.Row("<img src=x onerror=alert(1)> & \"friends\"")]);

        var html = TestData.Render(new HtmlExporter(), hostile);

        Assert.DoesNotContain("<script>", html);
        Assert.DoesNotContain("<img", html);
        Assert.DoesNotContain("<b>", html);
        Assert.Contains("&lt;img src=x onerror=alert(1)&gt; &amp; &quot;friends&quot;", html);
    }
}
