using CatalogProxies.Lazy;

namespace CatalogProxies.Tests;

public class AsyncLazyTests
{
    [Fact]
    public async Task Factory_does_not_run_until_the_value_is_requested()
    {
        var runs = 0;
        var lazy = new AsyncLazy<int>(_ => Task.FromResult(Interlocked.Increment(ref runs)));

        Assert.Equal(0, runs);
        Assert.False(lazy.IsStarted);
        Assert.False(lazy.TryGetValue(out _));

        Assert.Equal(1, await lazy.GetValueAsync());
        Assert.True(lazy.IsValueCreated);
        Assert.True(lazy.TryGetValue(out var value));
        Assert.Equal(1, value);
    }

    [Fact]
    public async Task Concurrent_callers_share_one_run_of_the_factory()
    {
        var runs = 0;
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var lazy = new AsyncLazy<string>(async _ =>
        {
            Interlocked.Increment(ref runs);
            await release.Task;
            return "ready";
        });

        var callers = Enumerable.Range(0, 32).Select(_ => Task.Run(() => lazy.GetValueAsync())).ToArray();
        await Task.Delay(50);
        release.SetResult();
        var results = await Task.WhenAll(callers);

        Assert.Equal(1, runs);
        Assert.All(results, r => Assert.Equal("ready", r));
    }

    [Fact]
    public async Task A_failed_attempt_is_not_cached_and_the_next_caller_retries()
    {
        var attempts = 0;
        var lazy = new AsyncLazy<int>(_ =>
            ++attempts == 1
                ? Task.FromException<int>(new InvalidOperationException("network blip"))
                : Task.FromResult(42));

        var error = await Assert.ThrowsAsync<InvalidOperationException>(() => lazy.GetValueAsync());
        Assert.Equal("network blip", error.Message);
        Assert.False(lazy.IsStarted);

        Assert.Equal(42, await lazy.GetValueAsync());
        Assert.Equal(2, attempts);
    }

    [Fact]
    public async Task A_synchronous_throw_from_the_factory_is_also_retried()
    {
        var attempts = 0;
        var lazy = new AsyncLazy<int>(_ => ++attempts == 1 ? throw new InvalidOperationException("boom") : Task.FromResult(7));

        await Assert.ThrowsAsync<InvalidOperationException>(() => lazy.GetValueAsync());
        Assert.Equal(7, await lazy.GetValueAsync());
    }

    [Fact]
    public async Task Cancelling_one_caller_does_not_cancel_the_shared_attempt()
    {
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var lazy = new AsyncLazy<int>(async _ =>
        {
            await release.Task;
            return 5;
        });

        using var cts = new CancellationTokenSource();
        var impatient = lazy.GetValueAsync(cts.Token);
        var patient = lazy.GetValueAsync();
        await cts.CancelAsync();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => impatient);
        release.SetResult();
        Assert.Equal(5, await patient);
        Assert.True(lazy.IsValueCreated);
    }
}
