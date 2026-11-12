using ReportGenerator.Cli;
using ReportGenerator.Exporters;
using ReportGenerator.Input;
using ReportGenerator.Model;

// Composition root: the only place that knows about files, the console and the registry.
// Exit codes: 0 success, 1 bad data, 2 bad usage.
try
{
    var options = CliOptions.Parse(args);
    if (options is null)
    {
        Console.WriteLine(CliOptions.Usage);
        return 0;
    }

    var exporter = ExporterRegistry.CreateDefault().Create(options.Format);
    var title = options.Title ?? Path.GetFileNameWithoutExtension(options.InputPath);

    Report report;
    using (var input = options.InputPath == "-" ? Console.In : new StreamReader(options.InputPath))
    {
        report = ReportLoader.FromCsv(title, input);
    }

    var exportOptions = new ExportOptions(options.IncludeTitle, options.IncludeSummary);
    if (options.OutputPath is null)
    {
        exporter.Export(report, Console.Out, exportOptions);
    }
    else
    {
        using var output = new StreamWriter(options.OutputPath);
        exporter.Export(report, output, exportOptions);
        Console.Error.WriteLine($"Wrote {report.Rows.Count} rows as {exporter.FormatName} to {options.OutputPath}");
    }

    return 0;
}
catch (Exception ex) when (ex is CliUsageException or UnknownFormatException)
{
    Console.Error.WriteLine($"error: {ex.Message}");
    Console.Error.WriteLine(CliOptions.Usage);
    return 2;
}
catch (Exception ex) when (ex is ReportValidationException or CsvFormatException or IOException or UnauthorizedAccessException)
{
    Console.Error.WriteLine($"error: {ex.Message}");
    return 1;
}
