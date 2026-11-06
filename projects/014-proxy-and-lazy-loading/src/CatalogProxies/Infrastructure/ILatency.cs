namespace CatalogProxies.Infrastructure;

/// <summary>Simulates the cost of talking to a remote store. Injected so tests can run at full speed.</summary>
public interface ILatency
{
    Task WaitAsync(CancellationToken cancellationToken);
}

/// <summary>Waits a fixed time per call, using a <see cref="TimeProvider"/> so the clock can be faked.</summary>
public sealed class FixedLatency : ILatency
{
    private readonly TimeSpan _delay;
    private readonly TimeProvider _time;

    public FixedLatency(TimeSpan delay, TimeProvider? time = null)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(delay, TimeSpan.Zero);
        _delay = delay;
        _time = time ?? TimeProvider.System;
    }

    public Task WaitAsync(CancellationToken cancellationToken) =>
        _delay == TimeSpan.Zero ? Task.CompletedTask : Task.Delay(_delay, _time, cancellationToken);
}

/// <summary>No delay at all.</summary>
public sealed class NoLatency : ILatency
{
    public static NoLatency Instance { get; } = new();

    private NoLatency()
    {
    }

    public Task WaitAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.CompletedTask;
    }
}
