using System.Collections.Concurrent;
using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using System.Runtime.ExceptionServices;

namespace CatalogProxies.Dynamic;

/// <summary>
/// <b>Dynamic proxy.</b> The other proxies here are written by hand for one interface.
/// This one is generated at runtime by <see cref="DispatchProxy"/> for <i>any</i> interface
/// and times every call, which is how logging, metrics and tracing interceptors work.
/// Create one with <see cref="TimingProxy.Create{T}"/>.
/// <para>
/// Synchronous methods, <see cref="Task"/> and <see cref="Task{TResult}"/> are timed until
/// they complete. Other awaitables (e.g. <c>ValueTask</c>) are timed until they are returned.
/// </para>
/// </summary>
#pragma warning disable CA1852 // DispatchProxy generates a subclass at runtime, so this type can't be sealed.
public class TimingProxy<T> : DispatchProxy
#pragma warning restore CA1852
    where T : class
{
    private static readonly MethodInfo WrapGenericTaskDefinition =
        typeof(TimingProxy<T>).GetMethod(nameof(WrapGenericTask), BindingFlags.NonPublic | BindingFlags.Instance)!;

    // One closed WrapGenericTask<TResult> per result type, built once.
    private static readonly ConcurrentDictionary<Type, MethodInfo> WrapGenericTaskByResultType = new();

    private T _target = null!;
    private IInvocationSink _sink = null!;
    private TimeProvider _time = null!;

    internal void Initialize(T target, IInvocationSink sink, TimeProvider time)
    {
        _target = target;
        _sink = sink;
        _time = time;
    }

    protected override object? Invoke(MethodInfo? targetMethod, object?[]? args)
    {
        ArgumentNullException.ThrowIfNull(targetMethod);
        var started = _time.GetTimestamp();

        object? result;
        try
        {
            result = targetMethod.Invoke(_target, args);
        }
        catch (TargetInvocationException ex) when (ex.InnerException is not null)
        {
            Report(targetMethod, started, ex.InnerException);
            ExceptionDispatchInfo.Capture(ex.InnerException).Throw();
            throw; // unreachable, keeps the compiler happy
        }

        var returnType = targetMethod.ReturnType;
        if (result is Task task && returnType.IsGenericType && returnType.GetGenericTypeDefinition() == typeof(Task<>))
        {
            var wrap = WrapGenericTaskByResultType.GetOrAdd(
                returnType.GetGenericArguments()[0],
                static resultType => WrapGenericTaskDefinition.MakeGenericMethod(resultType));
            return wrap.Invoke(this, [task, targetMethod, started]);
        }

        if (result is Task plainTask && returnType == typeof(Task))
        {
            return WrapTask(plainTask, targetMethod, started);
        }

        Report(targetMethod, started, error: null);
        return result;
    }

    private async Task WrapTask(Task task, MethodInfo method, long started)
    {
        try
        {
            await task.ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            Report(method, started, ex);
            throw;
        }

        Report(method, started, error: null);
    }

    private async Task<TResult> WrapGenericTask<TResult>(Task<TResult> task, MethodInfo method, long started)
    {
        TResult value;
        try
        {
            value = await task.ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            Report(method, started, ex);
            throw;
        }

        Report(method, started, error: null);
        return value;
    }

    private void Report(MethodInfo method, long started, Exception? error)
    {
        var outcome = error switch
        {
            null => InvocationOutcome.Succeeded,
            OperationCanceledException => InvocationOutcome.Canceled,
            _ => InvocationOutcome.Faulted,
        };
        _sink.Record(new InvocationRecord(typeof(T).Name, method.Name, _time.GetElapsedTime(started), outcome, error));
    }
}

/// <summary>Factory for <see cref="TimingProxy{T}"/>.</summary>
public static class TimingProxy
{
    /// <summary>Wraps <paramref name="target"/> in a proxy that implements <typeparamref name="T"/> and reports every call to <paramref name="sink"/>.</summary>
    [RequiresDynamicCode("DispatchProxy emits a type at runtime.")]
    public static T Create<T>(T target, IInvocationSink sink, TimeProvider? time = null)
        where T : class
    {
        ArgumentNullException.ThrowIfNull(target);
        ArgumentNullException.ThrowIfNull(sink);
        if (!typeof(T).IsInterface)
        {
            throw new ArgumentException($"{typeof(T).Name} must be an interface.", nameof(target));
        }

        var proxy = DispatchProxy.Create<T, TimingProxy<T>>();
        ((TimingProxy<T>)(object)proxy).Initialize(target, sink, time ?? TimeProvider.System);
        return proxy;
    }
}
