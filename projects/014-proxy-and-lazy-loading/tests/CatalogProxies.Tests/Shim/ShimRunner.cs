using System.Diagnostics;
using System.Globalization;
using System.Reflection;

namespace Xunit;

/// <summary>
/// Discovers [Fact]/[Theory] methods in this assembly and runs them with xUnit's lifecycle:
/// a fresh test-class instance per test, disposed afterwards. Optional argument: a substring
/// filter on "Class.Method".
/// </summary>
internal static class ShimRunner
{
    public static async Task<int> Main(string[] args)
    {
        var filter = args.FirstOrDefault();
        var tests = typeof(ShimRunner).Assembly.GetTypes()
            .Where(t => t is { IsClass: true, IsAbstract: false, IsPublic: true })
            .SelectMany(t => t.GetMethods(BindingFlags.Public | BindingFlags.Instance).Select(m => (Type: t, Method: m)))
            .Where(x => x.Method.GetCustomAttribute<FactAttribute>() is not null)
            .OrderBy(x => x.Type.Name, StringComparer.Ordinal)
            .ThenBy(x => x.Method.Name, StringComparer.Ordinal)
            .ToList();

        int passed = 0, failed = 0, skipped = 0;
        var clock = Stopwatch.StartNew();

        foreach (var (type, method) in tests)
        {
            var fact = method.GetCustomAttribute<FactAttribute>()!;
            var cases = fact is TheoryAttribute
                ? method.GetCustomAttributes<InlineDataAttribute>().Select(d => d.Data).ToList()
                : [[]];

            foreach (var data in cases)
            {
                var name = $"{type.Name}.{method.Name}" + (data.Length == 0 ? "" : $"({string.Join(", ", data)})");
                if (filter is not null && !name.Contains(filter, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                if (fact.Skip is not null)
                {
                    skipped++;
                    Console.WriteLine($"  SKIP  {name}: {fact.Skip}");
                    continue;
                }

                var error = await RunAsync(type, method, data);
                if (error is null)
                {
                    passed++;
                    Console.WriteLine($"  PASS  {name}");
                }
                else
                {
                    failed++;
                    Console.WriteLine($"  FAIL  {name}{Environment.NewLine}        {error.GetType().Name}: {error.Message}");
                }
            }
        }

        Console.WriteLine();
        Console.WriteLine($"Passed: {passed}, Failed: {failed}, Skipped: {skipped}, Time: {clock.Elapsed.TotalSeconds:0.00}s");
        return failed == 0 && passed > 0 ? 0 : 1;
    }

    private static async Task<Exception?> RunAsync(Type type, MethodInfo method, object?[] data)
    {
        object? instance = null;
        try
        {
            instance = Activator.CreateInstance(type);
            var parameters = method.GetParameters();
            var args = data.Select((value, i) => Convert(value, parameters[i].ParameterType)).ToArray();
            if (method.Invoke(instance, args) is Task task)
            {
                await task;
            }

            return null;
        }
        catch (TargetInvocationException ex) when (ex.InnerException is not null)
        {
            return ex.InnerException;
        }
        catch (Exception ex)
        {
            return ex;
        }
        finally
        {
            switch (instance)
            {
                case IAsyncDisposable asyncDisposable:
                    await asyncDisposable.DisposeAsync();
                    break;
                case IDisposable disposable:
                    disposable.Dispose();
                    break;
            }
        }
    }

    private static object? Convert(object? value, Type target) =>
        value is null || target.IsInstanceOfType(value)
            ? value
            : System.Convert.ChangeType(value, Nullable.GetUnderlyingType(target) ?? target, CultureInfo.InvariantCulture);
}
