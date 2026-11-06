using CatalogProxies.Dynamic;
using CatalogProxies.Tests.TestDoubles;

namespace CatalogProxies.Tests;

public interface ICalculator
{
    int Add(int a, int b);

    Task<int> AddSlowlyAsync(int a, int b);

    Task FailAsync();

    Task WaitForeverAsync(CancellationToken cancellationToken);
}

public sealed class Calculator(ManualTimeProvider clock) : ICalculator
{
    public int Add(int a, int b) => checked(a + b);

    public async Task<int> AddSlowlyAsync(int a, int b)
    {
        await Task.Yield();
        clock.Advance(TimeSpan.FromSeconds(5));
        return a + b;
    }

    public async Task FailAsync()
    {
        await Task.Yield();
        throw new InvalidOperationException("nope");
    }

    public Task WaitForeverAsync(CancellationToken cancellationToken) => Task.Delay(Timeout.Infinite, cancellationToken);
}

public class TimingProxyTests
{
    private readonly ManualTimeProvider _clock = new();
    private readonly InMemoryInvocationSink _sink = new();
    private readonly ICalculator _calculator;

    public TimingProxyTests() => _calculator = TimingProxy.Create<ICalculator>(new Calculator(_clock), _sink, _clock);

    [Fact]
    public void Synchronous_calls_are_forwarded_and_recorded()
    {
        Assert.Equal(5, _calculator.Add(2, 3));

        var record = Assert.Single(_sink.Records);
        Assert.Equal(new InvocationRecord("ICalculator", "Add", TimeSpan.Zero, InvocationOutcome.Succeeded), record);
    }

    [Fact]
    public async Task Async_calls_are_timed_until_the_task_completes()
    {
        Assert.Equal(9, await _calculator.AddSlowlyAsync(4, 5));

        var record = Assert.Single(_sink.Records);
        Assert.Equal("AddSlowlyAsync", record.Method);
        Assert.Equal(TimeSpan.FromSeconds(5), record.Elapsed);
    }

    [Fact]
    public void Synchronous_exceptions_keep_their_original_type()
    {
        Assert.Throws<OverflowException>(() => _calculator.Add(int.MaxValue, 1));

        var record = Assert.Single(_sink.Records);
        Assert.Equal(InvocationOutcome.Faulted, record.Outcome);
        Assert.IsType<OverflowException>(record.Error);
    }

    [Fact]
    public async Task Faulted_tasks_are_recorded_and_rethrown()
    {
        await Assert.ThrowsAsync<InvalidOperationException>(() => _calculator.FailAsync());

        Assert.Equal(InvocationOutcome.Faulted, Assert.Single(_sink.Records).Outcome);
    }

    [Fact]
    public async Task Cancelled_tasks_are_recorded_as_cancelled()
    {
        using var cts = new CancellationTokenSource();
        var waiting = _calculator.WaitForeverAsync(cts.Token);
        await cts.CancelAsync();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => waiting);
        Assert.Equal(InvocationOutcome.Canceled, Assert.Single(_sink.Records).Outcome);
    }

    [Fact]
    public void Only_interfaces_can_be_proxied()
    {
        Assert.Throws<ArgumentException>(() => TimingProxy.Create(new Calculator(_clock), _sink));
    }
}
