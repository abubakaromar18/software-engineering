namespace ReportGenerator.Model;

/// <summary>Per-column totals for the numeric columns of a report.</summary>
public sealed class ReportSummary
{
    private readonly IReadOnlyDictionary<string, decimal> _totals;

    private ReportSummary(int rowCount, IReadOnlyDictionary<string, decimal> totals)
    {
        RowCount = rowCount;
        _totals = totals;
    }

    public int RowCount { get; }

    /// <summary>The total for a numeric column, or null for non-numeric columns.</summary>
    public decimal? TotalFor(Column column) =>
        _totals.TryGetValue(column.Name, out var total) ? total : null;

    /// <summary>Sums every numeric column. Missing (null) cells count as zero.</summary>
    public static ReportSummary Compute(Report report)
    {
        ArgumentNullException.ThrowIfNull(report);
        var totals = new Dictionary<string, decimal>(StringComparer.OrdinalIgnoreCase);
        for (var i = 0; i < report.Columns.Count; i++)
        {
            var column = report.Columns[i];
            if (!column.Type.IsNumeric())
            {
                continue;
            }

            var index = i;
            totals[column.Name] = report.Rows.Sum(row => row[index] switch
            {
                long l => l,
                decimal d => d,
                _ => 0m,
            });
        }

        return new ReportSummary(report.Rows.Count, totals);
    }
}
