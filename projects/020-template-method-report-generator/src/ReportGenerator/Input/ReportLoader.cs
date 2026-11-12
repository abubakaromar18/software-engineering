using System.Globalization;
using ReportGenerator.Model;

namespace ReportGenerator.Input;

/// <summary>
/// Builds a <see cref="Report"/> from CSV text. The first record is the header.
/// Each column's type is inferred from its non-empty cells, choosing the narrowest
/// type that fits all of them: Integer, then Decimal, then Date (ISO yyyy-MM-dd),
/// otherwise Text. Empty cells become null ("missing").
/// </summary>
public static class ReportLoader
{
    private static readonly ColumnType[] InferenceOrder = [ColumnType.Integer, ColumnType.Decimal, ColumnType.Date];

    public static Report FromCsv(string title, TextReader reader)
    {
        var records = CsvParser.Parse(reader).ToList();
        if (records.Count == 0)
        {
            throw new ReportValidationException("The input is empty; expected a header row.");
        }

        var header = records[0];
        var body = records.Skip(1).ToList();
        for (var r = 0; r < body.Count; r++)
        {
            if (body[r].Length != header.Length)
            {
                throw new ReportValidationException(
                    $"Data row {r + 1} has {body[r].Length} fields but the header has {header.Length}.");
            }
        }

        var columns = header
            .Select((name, i) => new Column(name, InferType(body.Select(row => row[i]))))
            .ToArray();

        var rows = body.Select(record =>
            (IReadOnlyList<object?>)record.Select((text, i) => Convert(text, columns[i].Type)).ToArray());

        return new Report(title, columns, rows);
    }

    /// <summary>The narrowest type that every non-empty value parses as.</summary>
    public static ColumnType InferType(IEnumerable<string> values)
    {
        var present = values.Where(v => !string.IsNullOrWhiteSpace(v)).ToList();
        if (present.Count == 0)
        {
            return ColumnType.Text;
        }

        foreach (var candidate in InferenceOrder)
        {
            if (present.All(v => TryParse(v, candidate, out _)))
            {
                return candidate;
            }
        }

        return ColumnType.Text;
    }

    private static object? Convert(string text, ColumnType type)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return null;
        }

        // Inference guarantees the parse succeeds for every non-Text column.
        return TryParse(text, type, out var value) ? value : text;
    }

    private static bool TryParse(string text, ColumnType type, out object? value)
    {
        var trimmed = text.Trim();
        var invariant = CultureInfo.InvariantCulture;
        switch (type)
        {
            case ColumnType.Integer when long.TryParse(trimmed, NumberStyles.AllowLeadingSign, invariant, out var l):
                value = l;
                return true;
            case ColumnType.Decimal when decimal.TryParse(trimmed, NumberStyles.AllowLeadingSign | NumberStyles.AllowDecimalPoint, invariant, out var d):
                value = d;
                return true;
            case ColumnType.Date when DateOnly.TryParseExact(trimmed, "yyyy-MM-dd", invariant, DateTimeStyles.None, out var date):
                value = date;
                return true;
            case ColumnType.Text:
                value = text;
                return true;
            default:
                value = null;
                return false;
        }
    }
}
