using ReportGenerator.Exporters;
using ReportGenerator.Model;
using Xunit;

namespace ReportGenerator.Tests;

/// <summary>
/// Pins down the invariant part of the pattern: the order of steps in
/// <see cref="ReportExporter.Export"/> and how hooks gate the optional ones.
/// </summary>
public class TemplateMethodTests
{
    /// <summary>A spy subclass that records which steps the template calls, in order.</summary>
    private sealed class RecordingExporter(bool? titleHook = null, bool? summaryHook = null) : ReportExporter
    {
        public List<string> Calls { get; } = [];

        public override string FormatName => "spy";

        public override string FileExtension => ".spy";

        protected override void BeginDocument(Report report, TextWriter writer) => Calls.Add("begin");

        protected override void WriteTitle(string title, TextWriter writer) => Calls.Add($"title:{title}");

        protected override void WriteHeader(IReadOnlyList<Column> columns, TextWriter writer) => Calls.Add($"header:{columns.Count}");

        protected override void BeginRows(TextWriter writer) => Calls.Add("rows[");

        protected override void WriteRow(IReadOnlyList<Column> columns, IReadOnlyList<object?> row, int rowIndex, TextWriter writer) =>
            Calls.Add($"row:{rowIndex}");

        protected override void EndRows(int rowCount, TextWriter writer) => Calls.Add($"]rows:{rowCount}");

        protected override void WriteSummary(IReadOnlyList<Column> columns, ReportSummary summary, TextWriter writer) =>
            Calls.Add($"summary:{summary.RowCount}");

        protected override void EndDocument(Report report, TextWriter writer) => Calls.Add("end");

        protected override bool ShouldWriteTitle(ExportOptions options) => titleHook ?? base.ShouldWriteTitle(options);

        protected override bool ShouldWriteSummary(ExportOptions options) => summaryHook ?? base.ShouldWriteSummary(options);
    }

    [Fact]
    public void Export_calls_every_step_in_the_fixed_order()
    {
        var spy = new RecordingExporter();

        spy.Export(TestData.Sales(), TextWriter.Null);

        Assert.Equal(
            new[] { "begin", "title:Q3 Sales", "header:4", "rows[", "row:0", "row:1", "row:2", "]rows:3", "summary:3", "end" },
            spy.Calls);
    }

    [Fact]
    public void Options_switch_off_the_optional_steps_through_the_default_hooks()
    {
        var spy = new RecordingExporter();

        spy.Export(TestData.Sales(), TextWriter.Null, new ExportOptions(IncludeTitle: false, IncludeSummary: false));

        Assert.Equal(new[] { "begin", "header:4", "rows[", "row:0", "row:1", "row:2", "]rows:3", "end" }, spy.Calls);
    }

    [Fact]
    public void An_overridden_hook_wins_over_the_callers_option()
    {
        var spy = new RecordingExporter(titleHook: false, summaryHook: true);

        spy.Export(TestData.Sales(), TextWriter.Null, new ExportOptions(IncludeTitle: true, IncludeSummary: false));

        Assert.DoesNotContain("title:Q3 Sales", spy.Calls);
        Assert.Contains("summary:3", spy.Calls);
    }

    [Fact]
    public void An_empty_report_still_opens_and_closes_every_section()
    {
        var spy = new RecordingExporter();

        spy.Export(TestData.Empty(), TextWriter.Null);

        Assert.Equal(new[] { "begin", "title:Nothing", "header:1", "rows[", "]rows:0", "summary:0", "end" }, spy.Calls);
    }

    [Fact]
    public void Export_rejects_null_arguments()
    {
        var spy = new RecordingExporter();

        Assert.Throws<ArgumentNullException>(() => spy.Export(null!, TextWriter.Null));
        Assert.Throws<ArgumentNullException>(() => spy.Export(TestData.Sales(), null!));
        Assert.Empty(spy.Calls);
    }
}
