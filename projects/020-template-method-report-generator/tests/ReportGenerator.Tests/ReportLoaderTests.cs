using ReportGenerator.Input;
using ReportGenerator.Model;
using Xunit;

namespace ReportGenerator.Tests;

public class ReportLoaderTests
{
    [Theory]
    [InlineData("1|-20|300", ColumnType.Integer)]
    [InlineData("1|2.5|-3", ColumnType.Decimal)]
    [InlineData("2026-01-31|2026-02-01", ColumnType.Date)]
    [InlineData("1|two", ColumnType.Text)]
    [InlineData("2026-13-01", ColumnType.Text)]
    [InlineData("|  |", ColumnType.Text)]
    [InlineData("7||8", ColumnType.Integer)]
    public void Infers_the_narrowest_type_that_fits_every_value(string pipeSeparated, ColumnType expected)
    {
        Assert.Equal(expected, ReportLoader.InferType(pipeSeparated.Split('|')));
    }

    [Fact]
    public void Loads_typed_cells_and_treats_empty_cells_as_missing()
    {
        const string csv = "Name,Units,Price,When\nAda,3,1.50,2026-11-12\n\"Lovelace, A.\",,2,\n";

        var report = ReportLoader.FromCsv("t", new StringReader(csv));

        Assert.Equal(
            new[] { ColumnType.Text, ColumnType.Integer, ColumnType.Decimal, ColumnType.Date },
            report.Columns.Select(c => c.Type));
        Assert.Equal(new object?[] { "Ada", 3L, 1.50m, new DateOnly(2026, 11, 12) }, report.Rows[0]);
        Assert.Equal(new object?[] { "Lovelace, A.", null, 2m, null }, report.Rows[1]);
    }

    [Fact]
    public void Rejects_empty_input_and_ragged_rows()
    {
        Assert.Throws<ReportValidationException>(() => ReportLoader.FromCsv("t", new StringReader("")));

        var ex = Assert.Throws<ReportValidationException>(() => ReportLoader.FromCsv("t", new StringReader("A,B\n1,2\n3\n")));
        Assert.Contains("Data row 2 has 1 fields", ex.Message);
    }
}

public class CsvParserTests
{
    private static List<string[]> Parse(string text) => CsvParser.Parse(new StringReader(text)).ToList();

    [Fact]
    public void Handles_quotes_embedded_commas_newlines_and_crlf()
    {
        var records = Parse("a,\"b,c\",\"say \"\"hi\"\"\"\r\n\"multi\nline\",,end\r\n");

        Assert.Equal(2, records.Count);
        Assert.Equal(new[] { "a", "b,c", "say \"hi\"" }, records[0]);
        Assert.Equal(new[] { "multi\nline", "", "end" }, records[1]);
    }

    [Fact]
    public void Skips_blank_lines_and_accepts_a_missing_final_newline()
    {
        var records = Parse("a,b\n\n1,2");

        Assert.Equal(2, records.Count);
        Assert.Equal(new[] { "1", "2" }, records[1]);
    }

    [Fact]
    public void Keeps_a_record_made_only_of_an_empty_quoted_field()
    {
        Assert.Equal(new[] { "" }, Parse("\"\"\n").Single());
    }

    [Fact]
    public void Reports_malformed_quoting_with_the_line_number()
    {
        var unterminated = Assert.Throws<CsvFormatException>(() => Parse("a\n\"open\nstill open\n"));
        Assert.Equal(2, unterminated.Line);

        var stray = Assert.Throws<CsvFormatException>(() => Parse("ab\"c\n"));
        Assert.Equal(1, stray.Line);
    }
}
