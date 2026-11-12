using ReportGenerator.Model;
using Xunit;

namespace ReportGenerator.Tests;

public class ReportTests
{
    [Fact]
    public void Rejects_rows_with_the_wrong_number_of_cells()
    {
        var ex = Assert.Throws<ReportValidationException>(() =>
            new Report("t", [new Column("A", ColumnType.Text)], [TestData.Row("x", "y")]));

        Assert.Contains("Row 1 has 2 cells", ex.Message);
    }

    [Fact]
    public void Rejects_cells_that_do_not_match_the_column_type()
    {
        var ex = Assert.Throws<ReportValidationException>(() =>
            new Report("t", [new Column("Units", ColumnType.Integer)], [TestData.Row(1L), TestData.Row("many")]));

        Assert.Contains("Row 2, column 'Units': expected Integer but got String", ex.Message);
    }

    [Fact]
    public void Rejects_reports_without_columns_or_with_duplicate_names()
    {
        Assert.Throws<ReportValidationException>(() => new Report("t", [], []));
        Assert.Throws<ReportValidationException>(() =>
            new Report("t", [new Column("A", ColumnType.Text), new Column("a", ColumnType.Text)], []));
    }

    [Fact]
    public void Rows_are_copied_so_the_report_stays_immutable()
    {
        var cells = new object?[] { "before" };
        var report = new Report("t", [new Column("A", ColumnType.Text)], [cells]);

        cells[0] = "after";

        Assert.Equal("before", report.Rows[0][0]);
    }

    [Fact]
    public void Summary_sums_numeric_columns_and_treats_missing_as_zero()
    {
        var report = new Report(
            "t",
            [new Column("Name", ColumnType.Text), new Column("Units", ColumnType.Integer), new Column("Cost", ColumnType.Decimal)],
            [TestData.Row("a", 2L, 1.25m), TestData.Row("b", null, 0.75m), TestData.Row("c", 5L, null)]);

        var summary = ReportSummary.Compute(report);

        Assert.Equal(3, summary.RowCount);
        Assert.Equal(7m, summary.TotalFor(report.Columns[1]));
        Assert.Equal(2.00m, summary.TotalFor(report.Columns[2]));
        Assert.Null(summary.TotalFor(report.Columns[0]));
    }
}
