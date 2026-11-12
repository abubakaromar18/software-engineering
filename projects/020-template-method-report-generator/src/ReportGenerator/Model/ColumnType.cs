namespace ReportGenerator.Model;

/// <summary>The value type of every cell in a column.</summary>
#pragma warning disable CA1720 // The members deliberately name the data types users see in reports.
public enum ColumnType
{
    Text,
    Integer,
    Decimal,
    Date,
}
#pragma warning restore CA1720

/// <summary>Helpers for mapping between <see cref="ColumnType"/> and CLR types.</summary>
public static class ColumnTypeExtensions
{
    /// <summary>Numeric columns are the ones a summary can total.</summary>
    public static bool IsNumeric(this ColumnType type) => type is ColumnType.Integer or ColumnType.Decimal;

    /// <summary>True when <paramref name="value"/> is a legal cell for a column of this type (null means "missing").</summary>
    public static bool Accepts(this ColumnType type, object? value) => value is null || type switch
    {
        ColumnType.Text => value is string,
        ColumnType.Integer => value is long,
        ColumnType.Decimal => value is decimal,
        ColumnType.Date => value is DateOnly,
        _ => false,
    };
}
