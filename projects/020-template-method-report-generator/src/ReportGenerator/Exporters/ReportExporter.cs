using System.Globalization;
using ReportGenerator.Model;

namespace ReportGenerator.Exporters;

/// <summary>
/// The Template Method. <see cref="Export"/> fixes the skeleton of every export —
/// the order of the steps, when the summary is computed, and the guarantee that a
/// document is always closed — while subclasses fill in the format-specific steps.
/// <para>
/// Three kinds of members make up the contract:
/// <list type="bullet">
///   <item><b>Primitive operations</b> (<c>protected abstract</c>): every format must supply them.</item>
///   <item><b>Hooks</b> (<c>protected virtual</c>, with a sensible default): a format may override them.</item>
///   <item><b>The template method</b> (<see cref="Export"/>, public and non-virtual): nobody can reorder the steps.</item>
/// </list>
/// </para>
/// </summary>
public abstract class ReportExporter
{
    /// <summary>Short identifier used on the command line, e.g. "csv".</summary>
    public abstract string FormatName { get; }

    /// <summary>Conventional file extension including the dot, e.g. ".csv".</summary>
    public abstract string FileExtension { get; }

    /// <summary>
    /// Writes <paramref name="report"/> to <paramref name="writer"/>. This method is
    /// deliberately not virtual: it is the invariant algorithm that every format shares.
    /// </summary>
    public void Export(Report report, TextWriter writer, ExportOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(report);
        ArgumentNullException.ThrowIfNull(writer);
        options ??= ExportOptions.Default;

        BeginDocument(report, writer);

        if (ShouldWriteTitle(options))
        {
            WriteTitle(report.Title, writer);
        }

        WriteHeader(report.Columns, writer);

        BeginRows(writer);
        for (var i = 0; i < report.Rows.Count; i++)
        {
            WriteRow(report.Columns, report.Rows[i], i, writer);
        }

        EndRows(report.Rows.Count, writer);

        if (ShouldWriteSummary(options))
        {
            // Computed here, once, so no subclass can get the arithmetic wrong.
            WriteSummary(report.Columns, ReportSummary.Compute(report), writer);
        }

        EndDocument(report, writer);
        writer.Flush();
    }

    // ----- Primitive operations: every format must implement these. -----

    /// <summary>Opens the document (e.g. "&lt;html&gt;" or "{").</summary>
    protected abstract void BeginDocument(Report report, TextWriter writer);

    /// <summary>Writes the column headings.</summary>
    protected abstract void WriteHeader(IReadOnlyList<Column> columns, TextWriter writer);

    /// <summary>Writes one data row. <paramref name="rowIndex"/> is zero-based.</summary>
    protected abstract void WriteRow(IReadOnlyList<Column> columns, IReadOnlyList<object?> row, int rowIndex, TextWriter writer);

    /// <summary>Closes the document.</summary>
    protected abstract void EndDocument(Report report, TextWriter writer);

    // ----- Hooks: sensible defaults that a format may override. -----

    /// <summary>Whether this format writes a title. Defaults to the caller's option.</summary>
    protected virtual bool ShouldWriteTitle(ExportOptions options) => options.IncludeTitle;

    /// <summary>Whether this format writes a summary. Defaults to the caller's option.</summary>
    protected virtual bool ShouldWriteSummary(ExportOptions options) => options.IncludeSummary;

    /// <summary>Writes the title. Default: nothing, for formats with no natural place for one.</summary>
    protected virtual void WriteTitle(string title, TextWriter writer)
    {
    }

    /// <summary>Called before the first row. Default: nothing.</summary>
    protected virtual void BeginRows(TextWriter writer)
    {
    }

    /// <summary>Called after the last row, even when there are none. Default: nothing.</summary>
    protected virtual void EndRows(int rowCount, TextWriter writer)
    {
    }

    /// <summary>Writes the totals. Default: nothing, for formats with no natural place for them.</summary>
    protected virtual void WriteSummary(IReadOnlyList<Column> columns, ReportSummary summary, TextWriter writer)
    {
    }

    /// <summary>
    /// Turns a cell into text. The default is culture-invariant and lossless so that
    /// machine-readable formats round-trip; presentation formats override it.
    /// </summary>
    protected virtual string FormatValue(object? value, Column column) => value switch
    {
        null => string.Empty,
        DateOnly date => date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
        IFormattable formattable => formattable.ToString(null, CultureInfo.InvariantCulture),
        _ => value.ToString() ?? string.Empty,
    };
}
