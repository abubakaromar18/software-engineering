using System.Diagnostics;
using System.Globalization;
using System.Reflection;
using Xunit;

// Discovers [Fact]/[Theory] methods by reflection and runs them xUnit-style:
// a fresh instance of the test class per test case. Exit code = failures (capped).
var cases =
    from type in typeof(Program).Assembly.GetTypes()
    where type is { IsClass: true, IsAbstract: false, IsPublic: true }
    from method in type.GetMethods(BindingFlags.Public | BindingFlags.Instance)
    where method.GetCustomAttribute<FactAttribute>() is not null
    orderby type.Name, method.MetadataToken
    from data in method.GetCustomAttribute<TheoryAttribute>() is null
        ? [Array.Empty<object?>()]
        : method.GetCustomAttributes<InlineDataAttribute>().Select(d => d.Data)
    select (type, method, data);

int passed = 0, failed = 0;
var clock = Stopwatch.StartNew();
foreach (var (type, method, data) in cases)
{
    var name = data.Length == 0
        ? $"{type.Name}.{method.Name}"
        : $"{type.Name}.{method.Name}({string.Join(", ", data.Select(a => a is string s ? $"\"{s.ReplaceLineEndings("\\n")}\"" : Convert.ToString(a, CultureInfo.InvariantCulture)))})";
    try
    {
        method.Invoke(Activator.CreateInstance(type), data);
        passed++;
    }
    catch (TargetInvocationException ex)
    {
        failed++;
        Console.WriteLine($"FAIL {name}\n     {ex.InnerException?.Message.ReplaceLineEndings("\n     ")}");
    }
}

Console.WriteLine($"\nPassed: {passed}, Failed: {failed}, Total: {passed + failed} ({clock.ElapsedMilliseconds} ms)");
return Math.Min(failed, 100);
