namespace ReportGenerator.Cli;

/// <summary>Parsed command-line arguments.</summary>
internal sealed record CliOptions(
    string InputPath,
    string Format,
    string? Title,
    string? OutputPath,
    bool IncludeTitle,
    bool IncludeSummary)
{
    public const string Usage = """
        Usage: report-gen <input.csv> [options]

        Options:
          -f, --format <csv|json|html>   Output format (default: html)
          -t, --title <text>             Report title (default: input file name)
          -o, --output <path>            Write to a file instead of stdout
              --no-title                 Omit the title
              --no-summary               Omit the totals
          -h, --help                     Show this help
        """;

    /// <summary>Parses <paramref name="args"/>; returns null when help was requested.</summary>
    public static CliOptions? Parse(IReadOnlyList<string> args)
    {
        string? input = null, title = null, output = null;
        var format = "html";
        bool includeTitle = true, includeSummary = true;

        for (var i = 0; i < args.Count; i++)
        {
            var arg = args[i];
            switch (arg)
            {
                case "-h" or "--help":
                    return null;
                case "-f" or "--format":
                    format = ValueAfter(args, ref i);
                    break;
                case "-t" or "--title":
                    title = ValueAfter(args, ref i);
                    break;
                case "-o" or "--output":
                    output = ValueAfter(args, ref i);
                    break;
                case "--no-title":
                    includeTitle = false;
                    break;
                case "--no-summary":
                    includeSummary = false;
                    break;
                case var _ when arg.StartsWith('-') && arg != "-":
                    throw new CliUsageException($"Unknown option '{arg}'.");
                case var _ when input is null:
                    input = arg;
                    break;
                default:
                    throw new CliUsageException($"Unexpected argument '{arg}'; only one input file is allowed.");
            }
        }

        return input is null
            ? throw new CliUsageException("Missing input file.")
            : new CliOptions(input, format, title, output, includeTitle, includeSummary);
    }

    private static string ValueAfter(IReadOnlyList<string> args, ref int i) =>
        ++i < args.Count ? args[i] : throw new CliUsageException($"Option '{args[i - 1]}' needs a value.");
}

/// <summary>Raised for invalid command-line usage.</summary>
internal sealed class CliUsageException(string message) : Exception(message);
