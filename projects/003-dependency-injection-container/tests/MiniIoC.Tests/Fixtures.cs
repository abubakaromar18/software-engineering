// Small service graphs shared by the tests. Kept deliberately tiny and named after
// their role in the test, not after a business domain.
namespace MiniIoC.Tests;

public interface IClock { DateTime Now { get; } }
public sealed class FixedClock : IClock { public DateTime Now => new(2026, 1, 1); }
public sealed class OtherClock : IClock { public DateTime Now => DateTime.MinValue; }

public interface IGreeter { string Greet(string name); }
public sealed class Greeter(IClock clock) : IGreeter
{
    public IClock Clock { get; } = clock;
    public string Greet(string name) => $"Hello {name}, it is {Clock.Now:yyyy}";
}

public interface IUnitOfWork { }
public sealed class UnitOfWork : IUnitOfWork { }

public sealed class Counter
{
    private static int s_created;
    public Counter() => Interlocked.Increment(ref s_created);
    public static int Created => Volatile.Read(ref s_created);
}

// ---- constructor selection --------------------------------------------------

public sealed class MultiCtor
{
    public MultiCtor() => Used = "none";
    public MultiCtor(IClock clock) => Used = "clock";
    public MultiCtor(IClock clock, IGreeter greeter) => Used = "clock+greeter";
    public string Used { get; }
}

public sealed class WithOptional(IClock clock, int retries = 3, string? name = null)
{
    public IClock Clock { get; } = clock;
    public int Retries { get; } = retries;
    public string? Name { get; } = name;
}

public sealed class Ambiguous
{
    public Ambiguous(IClock clock) => _ = clock;
    public Ambiguous(IUnitOfWork unitOfWork) => _ = unitOfWork;
}

public sealed class NeedsMissing(IGreeter greeter, IDisposable missing)
{
    public IGreeter Greeter { get; } = greeter;
    public IDisposable Missing { get; } = missing;
}

public sealed class NoPublicCtor { private NoPublicCtor() { } }

public sealed class ThrowingCtor
{
    public ThrowingCtor() => throw new InvalidOperationException("boom");
}

// ---- cycles -----------------------------------------------------------------

public sealed class CycleA(CycleB b) { public CycleB B { get; } = b; }
public sealed class CycleB(CycleC c) { public CycleC C { get; } = c; }
public sealed class CycleC(CycleA a) { public CycleA A { get; } = a; }
public sealed class SelfCycle(SelfCycle self) { public SelfCycle Self { get; } = self; }

public interface IPlugin { }
public sealed class PluginHost(IEnumerable<IPlugin> plugins) : IPlugin
{
    public IEnumerable<IPlugin> Plugins { get; } = plugins;
}

// ---- lifetimes & captive dependencies ----------------------------------------

public sealed class SingletonNeedsScoped(IUnitOfWork unitOfWork) { public IUnitOfWork UnitOfWork { get; } = unitOfWork; }
public sealed class TransientNeedsScoped(IUnitOfWork unitOfWork) { public IUnitOfWork UnitOfWork { get; } = unitOfWork; }
public sealed class SingletonNeedsTransientNeedsScoped(TransientNeedsScoped inner) { public TransientNeedsScoped Inner { get; } = inner; }
public sealed class SingletonNeedsProvider(IServiceProvider provider) { public IServiceProvider Provider { get; } = provider; }

// ---- generics ---------------------------------------------------------------

public interface IRepository<T> { Type EntityType { get; } }
public sealed class Repository<T> : IRepository<T> { public Type EntityType => typeof(T); }
public sealed class CachedRepository<T> : IRepository<T> { public Type EntityType => typeof(T); }
public sealed class ValueOnlyRepository<T> : IRepository<T> where T : struct { public Type EntityType => typeof(T); }
public sealed class User { }
public sealed class Order { }
public sealed class UserService(IRepository<User> users) { public IRepository<User> Users { get; } = users; }

// ---- disposal ---------------------------------------------------------------

public sealed class DisposalLog
{
    private readonly List<string> _entries = [];
    public IReadOnlyList<string> Entries { get { lock (_entries) { return [.. _entries]; } } }
    public void Add(string entry) { lock (_entries) { _entries.Add(entry); } }
}

public sealed class TrackedA(DisposalLog log) : IDisposable
{
    public bool IsDisposed { get; private set; }
    public void Dispose() { IsDisposed = true; log.Add("A"); }
}

public sealed class TrackedB(DisposalLog log, TrackedA a) : IDisposable
{
    public TrackedA A { get; } = a;
    public void Dispose() => log.Add("B");
}

public sealed class AsyncOnly(DisposalLog log) : IAsyncDisposable
{
    public ValueTask DisposeAsync() { log.Add("async"); return ValueTask.CompletedTask; }
}

public sealed class FailingDispose : IDisposable
{
    public void Dispose() => throw new InvalidOperationException("dispose failed");
}
