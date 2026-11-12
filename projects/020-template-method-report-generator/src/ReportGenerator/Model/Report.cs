using System.Globalization;

namespace ReportGenerator.Model;

/// <summary>
/// An immutable, validated table of data: a title, typed columns and rows whose
/// cells match those types. Construction is the only validation point, so every
/// exporter can trust what it receives.
/// </summary>
public sealed class Report
{
    public Report(string title, IEnumerable<Column> columns, IEnumerable<IReadOnlyList<object?>> rows)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(title);
        ArgumentNullException.ThrowIfNull(columns);
        ArgumentNullException.ThrowIfNull(rows);

        Title = title.Trim();
        Columns = columns.ToArray();
        if (Columns.Count == 0)
        {
            throw new ReportValidationException("A report needs at least one column.");
        }

        var duplicate = Columns.GroupBy(c => c.Name, StringComparer.OrdinalIgnoreCase).FirstOrDefault(g => g.Count() > 1);
        if (duplicate is not null)
        {
            throw new ReportValidationException($"Duplicate column name '{duplicate.Key}'.");
        }

        Rows = rows.Select((row, index) => ValidateRow(row, index)).ToArray();
    }

    public string Title { get; }

    public IReadOnlyList<Column> Columns { get; }

    public IReadOnlyList<IReadOnlyList<object?>> Rows { get; }

    private object?[] ValidateRow(IReadOnlyList<object?> row, int index)
    {
        ArgumentNullException.ThrowIfNull(row);
        if (row.Count != Columns.Count)
        {
            throw new ReportValidationException(
                $"Row {index + 1} has {row.Count} cells but the report has {Columns.Count} columns.");
        }

        for (var i = 0; i < row.Count; i++)
        {
            var column = Columns[i];
            if (!column.Type.Accepts(row[i]))
            {
                throw new ReportValidationException(string.Create(CultureInfo.InvariantCulture,
                    $"Row {index + 1}, column '{column.Name}': expected {column.Type} but got {row[i]!.GetType().Name}."));
            }
        }

        return row.ToArray(); // defensive copy keeps the report immutable
    }
}

/// <summary>Raised when report data is structurally invalid.</summary>
public sealed class ReportValidationException(string message) : Exception(message);
