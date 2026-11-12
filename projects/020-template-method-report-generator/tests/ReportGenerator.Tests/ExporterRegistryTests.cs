using ReportGenerator.Exporters;
using ReportGenerator.Model;
using Xunit;

namespace ReportGenerator.Tests;

public class ExporterRegistryTests
{
    /// <summary>
    /// Proof of extensibility: a whole new format in a few lines, touching no
    /// library code. It overrides only the four primitive steps and the title hook.
    /// </summary>
    private sealed class MarkdownExporter : ReportExporter
    {
        public override string FormatName => "md";

        public override string FileExtension => ".md";

        protected override void BeginDocument(Report report, TextWriter writer)
        {
        }

        protected override void WriteTitle(string title, TextWriter writer) => writer.Write($"# {title}\n\n");

        protected override void WriteHeader(IReadOnlyList<Column> columns, TextWriter writer)
        {
            writer.Write($"| {string.Join(" | ", columns.Select(c => c.Name))} |\n");
            writer.Write($"|{string.Concat(columns.Select(c => c.Type.IsNumeric() ? "---:|" : "---|"))}\n");
        }

        protected override void WriteRow(IReadOnlyList<Column> columns, IReadOnlyList<object?> row, int rowIndex, TextWriter writer) =>
            writer.Write($"| {string.Join(" | ", row.Select((v, i) => FormatValue(v, columns[i])))} |\n");

        protected override void EndDocument(Report report, TextWriter writer)
        {
        }
    }

    [Theory]
    [InlineData("csv", typeof(CsvExporter))]
    [InlineData("JSON", typeof(JsonExporter))]
    [InlineData("Html", typeof(HtmlExporter))]
    public void Default_registry_resolves_formats_case_insensitively(string format, Type expected)
    {
        Assert.Equal(expected, ExporterRegistry.CreateDefault().Create(format).GetType());
    }

    [Fact]
    public void Unknown_format_lists_the_known_ones()
    {
        var ex = Assert.Throws<UnknownFormatException>(() => ExporterRegistry.CreateDefault().Create("xml"));

        Assert.Equal("xml", ex.Format);
        Assert.Contains("csv, html, json", ex.Message);
    }

    [Fact]
    public void Duplicate_registration_is_refused()
    {
        Assert.Throws<InvalidOperationException>(() => ExporterRegistry.CreateDefault().Register("CSV", () => new CsvExporter()));
    }

    [Fact]
    public void A_new_format_plugs_in_without_changing_the_library()
    {
        var registry = ExporterRegistry.CreateDefault().Register("md", () => new MarkdownExporter());

        var markdown = TestData.Render(registry.Create("md"), TestData.Sales());

        Assert.Equal(new[] { "csv", "html", "json", "md" }, registry.Formats);
        Assert.StartsWith("# Q3 Sales\n\n| Region | Units | Revenue | Shipped |\n|---|---:|---:|---|\n| North | 1200 | 5400.00 | 2026-07-03 |", markdown);
    }
}
