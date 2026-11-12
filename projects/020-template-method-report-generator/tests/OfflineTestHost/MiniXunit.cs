// A deliberately tiny stand-in for the parts of xUnit this suite uses, so the
// real test sources compile and run where NuGet is unreachable. It is not a
// general-purpose framework: anything the suite does not use is left out.
using System.Collections;

namespace Xunit;

[AttributeUsage(AttributeTargets.Method)]
public class FactAttribute : Attribute;

[AttributeUsage(AttributeTargets.Method)]
public sealed class TheoryAttribute : FactAttribute;

[AttributeUsage(AttributeTargets.Method, AllowMultiple = true)]
public sealed class InlineDataAttribute(params object?[] data) : Attribute
{
    public object?[] Data { get; } = data;
}

/// <summary>Raised by every failed assertion.</summary>
public sealed class AssertionException(string message) : Exception(message);

public static class Assert
{
    public static void True(bool condition) => Check(condition, "Expected true but was false.");

    public static void False(bool condition) => Check(!condition, "Expected false but was true.");

    public static void Null(object? value) => Check(value is null, $"Expected null but was <{value}>.");

    public static void Equal<T>(T expected, T actual)
    {
        // Like xUnit, compare collections element by element rather than by reference.
        if (expected is IEnumerable e && actual is IEnumerable a && expected is not string)
        {
            Equal(e.Cast<object?>(), a.Cast<object?>());
            return;
        }

        Check(EqualityComparer<T>.Default.Equals(expected, actual), $"Expected <{Show(expected)}> but was <{Show(actual)}>.");
    }

    public static void Equal<T>(IEnumerable<T> expected, IEnumerable<T> actual)
    {
        var e = expected.ToList();
        var a = actual.ToList();
        Check(e.SequenceEqual(a), $"Sequences differ.\n  expected: [{string.Join(", ", e.Select(x => Show(x)))}]\n  actual:   [{string.Join(", ", a.Select(x => Show(x)))}]");
    }

    public static void Contains(string expectedSubstring, string actual) =>
        Check(actual.Contains(expectedSubstring, StringComparison.Ordinal), $"Expected to find <{expectedSubstring}> in:\n{actual}");

    public static void DoesNotContain(string unexpected, string actual) =>
        Check(!actual.Contains(unexpected, StringComparison.Ordinal), $"Did not expect <{unexpected}> in:\n{actual}");

    public static void Contains<T>(T expected, IEnumerable<T> collection) =>
        Check(collection.Contains(expected), $"Collection does not contain <{Show(expected)}>.");

    public static void DoesNotContain<T>(T unexpected, IEnumerable<T> collection) =>
        Check(!collection.Contains(unexpected), $"Collection unexpectedly contains <{Show(unexpected)}>.");

    public static void StartsWith(string expectedStart, string actual) =>
        Check(actual.StartsWith(expectedStart, StringComparison.Ordinal), $"Expected to start with <{expectedStart}> but was:\n{actual}");

    public static void EndsWith(string expectedEnd, string actual) =>
        Check(actual.EndsWith(expectedEnd, StringComparison.Ordinal), $"Expected to end with <{expectedEnd}> but was:\n{actual}");

    public static void Empty(IEnumerable collection) =>
        Check(!collection.GetEnumerator().MoveNext(), "Expected an empty collection.");

    public static T Throws<T>(Action action) where T : Exception
    {
        try
        {
            action();
        }
        catch (Exception ex) when (ex.GetType() == typeof(T))
        {
            return (T)ex;
        }
        catch (Exception ex)
        {
            throw new AssertionException($"Expected {typeof(T).Name} but got {ex.GetType().Name}: {ex.Message}");
        }

        throw new AssertionException($"Expected {typeof(T).Name} but nothing was thrown.");
    }

    public static T Throws<T>(Func<object?> func) where T : Exception => Throws<T>(() => { func(); });

    private static void Check(bool condition, string message)
    {
        if (!condition)
        {
            throw new AssertionException(message);
        }
    }

    private static string Show(object? value) => value switch
    {
        null => "null",
        string s => $"\"{s}\"",
        _ => value.ToString() ?? "",
    };
}
