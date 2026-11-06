namespace CatalogProxies.Dynamic;

/// <summary>One intercepted call. For async methods, <see cref="Elapsed"/> runs until the task completes.</summary>
public sealed record InvocationRecord(string Interface, string Method, TimeSpan Elapsed, InvocationOutcome Outcome, Exception? Error = null);

public enum InvocationOutcome
{
    Succeeded,
    Faulted,
    Canceled,
}

/// <summary>Where a <see cref="TimingProxy{T}"/> reports calls (a log, a metrics library, a test).</summary>
public interface IInvocationSink
{
    void Record(InvocationRecord invocation);
}

/// <summary>Keeps every record in memory. Thread-safe.</summary>
public sealed class InMemoryInvocationSink : IInvocationSink
{
    private readonly System.Collections.Concurrent.ConcurrentQueue<InvocationRecord> _records = new();

    public IReadOnlyList<InvocationRecord> Records => _records.ToArray();

    public void Record(InvocationRecord invocation) => _records.Enqueue(invocation);
}
