// Offline shim: a tiny, source-compatible subset of xUnit, compiled only with -p:OfflineTests=true.
// It lets the suite run where NuGet is unreachable. With NuGet, the real xUnit packages are used.
namespace Xunit;

[AttributeUsage(AttributeTargets.Method)]
public class FactAttribute : Attribute
{
    public string? Skip { get; set; }
}

[AttributeUsage(AttributeTargets.Method)]
public sealed class TheoryAttribute : FactAttribute
{
}

[AttributeUsage(AttributeTargets.Method, AllowMultiple = true)]
public sealed class InlineDataAttribute(params object?[] data) : Attribute
{
    public object?[] Data { get; } = data;
}
