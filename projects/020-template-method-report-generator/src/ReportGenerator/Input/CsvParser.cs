using System.Text;

namespace ReportGenerator.Input;

/// <summary>
/// A small RFC 4180 reader: quoted fields, doubled quotes, embedded commas and
/// line breaks, and either LF or CRLF line endings. Blank lines are skipped.
/// </summary>
public static class CsvParser
{
    public static IEnumerable<string[]> Parse(TextReader reader)
    {
        ArgumentNullException.ThrowIfNull(reader);
        var fields = new List<string>();
        var field = new StringBuilder();
        var inQuotes = false;
        var line = 1;
        var quoteStartLine = 0;
        var recordHasContent = false;

        int next;
        while ((next = reader.Read()) != -1)
        {
            var c = (char)next;
            if (inQuotes)
            {
                if (c == '"')
                {
                    if (reader.Peek() == '"')
                    {
                        field.Append('"');
                        reader.Read();
                    }
                    else
                    {
                        inQuotes = false;
                    }
                }
                else
                {
                    if (c == '\n')
                    {
                        line++;
                    }

                    field.Append(c);
                }

                continue;
            }

            switch (c)
            {
                case '"' when field.Length == 0:
                    inQuotes = true;
                    quoteStartLine = line;
                    recordHasContent = true;
                    break;
                case '"':
                    throw new CsvFormatException(line, "a quote may only start a field");
                case ',':
                    fields.Add(field.ToString());
                    field.Clear();
                    recordHasContent = true;
                    break;
                case '\r':
                    break; // part of CRLF; the '\n' ends the record
                case '\n':
                    if (recordHasContent || field.Length > 0)
                    {
                        fields.Add(field.ToString());
                        yield return fields.ToArray();
                    }

                    fields.Clear();
                    field.Clear();
                    recordHasContent = false;
                    line++;
                    break;
                default:
                    field.Append(c);
                    recordHasContent = true;
                    break;
            }
        }

        if (inQuotes)
        {
            throw new CsvFormatException(quoteStartLine, "quoted field is never closed");
        }

        if (recordHasContent || field.Length > 0)
        {
            fields.Add(field.ToString());
            yield return fields.ToArray();
        }
    }
}

/// <summary>Raised for malformed CSV input, with the line it was detected on.</summary>
public sealed class CsvFormatException(int line, string problem)
    : Exception($"CSV line {line}: {problem}.")
{
    public int Line { get; } = line;
}
