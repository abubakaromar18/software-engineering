using System.Collections;

namespace Xunit;

/// <summary>Thrown when an assertion fails.</summary>
public sealed class AssertFailedException(string message) : Exception(message);

/// <summary>The subset of xUnit's Assert API this suite uses, with the same semantics.</summary>
#pragma warning disable CA1720 // Names must match xUnit's (Single).
public static class Assert
{
    public static void Equal<T>(T expected, T actual)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
        {
            Fail($"Expected: {Show(expected)}{Environment.NewLine}Actual:   {Show(actual)}");
        }
    }

    public static void Equal(string? expected, string? actual) => Equal<string?>(expected, actual);

    public static void Equal<T>(IEnumerable<T> expected, IEnumerable<T> actual)
    {
        var e = expected.ToList();
        var a = actual.ToList();
        if (!e.SequenceEqual(a))
        {
            Fail($"Expected: [{string.Join(", ", e.Select(x => Show(x)))}]{Environment.NewLine}Actual:   [{string.Join(", ", a.Select(x => Show(x)))}]");
        }
    }

    public static void NotEqual<T>(T expected, T actual)
    {
        if (EqualityComparer<T>.Default.Equals(expected, actual))
        {
            Fail($"Expected anything but {Show(expected)}");
        }
    }

    public static void True(bool condition, string? userMessage = null)
    {
        if (!condition)
        {
            Fail(userMessage ?? "Expected true");
        }
    }

    public static void False(bool condition, string? userMessage = null)
    {
        if (condition)
        {
            Fail(userMessage ?? "Expected false");
        }
    }

    public static void Null(object? value)
    {
        if (value is not null)
        {
            Fail($"Expected null but got {Show(value)}");
        }
    }

    public static void NotNull(object? value)
    {
        if (value is null)
        {
            Fail("Expected a value but got null");
        }
    }

    public static void Same(object? expected, object? actual)
    {
        if (!ReferenceEquals(expected, actual))
        {
            Fail("Expected the same instance");
        }
    }

    public static void NotSame(object? expected, object? actual)
    {
        if (ReferenceEquals(expected, actual))
        {
            Fail("Expected different instances");
        }
    }

    public static void Empty(IEnumerable collection)
    {
        if (collection.Cast<object?>().Any())
        {
            Fail("Expected an empty collection");
        }
    }

    public static T Single<T>(IEnumerable<T> collection)
    {
        var items = collection.Take(2).ToList();
        if (items.Count != 1)
        {
            Fail($"Expected exactly one item but found {collection.Count()}");
        }

        return items[0];
    }

    public static void Contains(string expectedSubstring, string? actual)
    {
        if (actual is null || !actual.Contains(expectedSubstring, StringComparison.Ordinal))
        {
            Fail($"Expected {Show(actual)} to contain {Show(expectedSubstring)}");
        }
    }

    public static void Contains<T>(T expected, IEnumerable<T> collection)
    {
        if (!collection.Contains(expected))
        {
            Fail($"Expected the collection to contain {Show(expected)}");
        }
    }

    public static void All<T>(IEnumerable<T> collection, Action<T> action)
    {
        foreach (var item in collection)
        {
            action(item);
        }
    }

    public static T IsType<T>(object? value)
    {
        if (value is null || value.GetType() != typeof(T))
        {
            Fail($"Expected type {typeof(T).Name} but got {value?.GetType().Name ?? "null"}");
        }

        return (T)value!;
    }

    public static void IsNotType<T>(object? value)
    {
        if (value is not null && value.GetType() == typeof(T))
        {
            Fail($"Expected anything but type {typeof(T).Name}");
        }
    }

    public static T Throws<T>(Action action)
        where T : Exception
    {
        try
        {
            action();
        }
        catch (Exception ex)
        {
            return ExactType<T>(ex);
        }

        throw new AssertFailedException($"Expected {typeof(T).Name} but nothing was thrown");
    }

    public static async Task<T> ThrowsAsync<T>(Func<Task> action)
        where T : Exception
    {
        try
        {
            await action();
        }
        catch (Exception ex)
        {
            return ExactType<T>(ex);
        }

        throw new AssertFailedException($"Expected {typeof(T).Name} but nothing was thrown");
    }

    public static async Task<T> ThrowsAnyAsync<T>(Func<Task> action)
        where T : Exception
    {
        try
        {
            await action();
        }
        catch (T ex)
        {
            return ex;
        }
        catch (Exception ex)
        {
            throw new AssertFailedException($"Expected {typeof(T).Name} or a subclass but got {ex.GetType().Name}: {ex.Message}");
        }

        throw new AssertFailedException($"Expected {typeof(T).Name} but nothing was thrown");
    }

    private static T ExactType<T>(Exception ex)
        where T : Exception =>
        ex.GetType() == typeof(T)
            ? (T)ex
            : throw new AssertFailedException($"Expected {typeof(T).Name} but got {ex.GetType().Name}: {ex.Message}");

    [System.Diagnostics.CodeAnalysis.DoesNotReturn]
    private static void Fail(string message) => throw new AssertFailedException(message);

    private static string Show(object? value) => value switch
    {
        null => "null",
        string s => $"\"{s}\"",
        _ => value.ToString() ?? "?",
    };
}
#pragma warning restore CA1720
