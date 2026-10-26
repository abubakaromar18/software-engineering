namespace MiniIoC.Demo;

// A tiny "order processing" app: enough moving parts to show every lifetime.

internal interface IClock { DateTimeOffset UtcNow { get; } }

internal sealed class SystemClock : IClock
{
    public DateTimeOffset UtcNow => DateTimeOffset.UtcNow;
}

/// <summary>Singleton: one log shared by the whole app.</summary>
internal sealed class ConsoleLog
{
    private int _next;
    public void Write(string message) =>
        Console.WriteLine($"  [{Interlocked.Increment(ref _next):00}] {message}");
}

/// <summary>Scoped: one per request, like a database transaction.</summary>
internal sealed class UnitOfWork(ConsoleLog log) : IDisposable
{
    public Guid Id { get; } = Guid.NewGuid();

    public string ShortId => Id.ToString("N")[..6];

    public void Dispose() => log.Write($"UnitOfWork {ShortId} disposed (end of request)");
}

internal interface IRepository<T>
{
    void Save(T entity);
}

/// <summary>Open generic, scoped: closed per entity type, sharing the request's unit of work.</summary>
internal sealed class Repository<T>(UnitOfWork unitOfWork, ConsoleLog log) : IRepository<T>
{
    public void Save(T entity) =>
        log.Write($"Repository<{typeof(T).Name}> saved {entity} in UnitOfWork {unitOfWork.ShortId}");
}

internal sealed record Order(int Number, decimal Total);

internal interface IOrderValidator
{
    string? Validate(Order order);
}

internal sealed class PositiveTotalValidator : IOrderValidator
{
    public string? Validate(Order order) => order.Total > 0 ? null : "total must be positive";
}

internal sealed class NotFromTheFutureValidator(IClock clock) : IOrderValidator
{
    // Placeholder rule that exercises a dependency; real code would look at an order date.
    public string? Validate(Order order) => clock.UtcNow.Year >= 2000 ? null : "clock is wrong";
}

/// <summary>Transient: receives every validator via IEnumerable&lt;T&gt;.</summary>
internal sealed class OrderService(
    IRepository<Order> orders,
    IEnumerable<IOrderValidator> validators,
    ConsoleLog log)
{
    public void Place(Order order)
    {
        var errors = validators.Select(v => v.Validate(order)).OfType<string>().ToList();
        if (errors.Count > 0)
        {
            log.Write($"Order {order.Number} rejected: {string.Join("; ", errors)}");
            return;
        }

        orders.Save(order);
    }
}

// ---- deliberately broken graphs, used to demonstrate diagnostics -------------

internal sealed class AuditTrail(NotificationHub hub) { public NotificationHub Hub { get; } = hub; }

internal sealed class NotificationHub(AuditTrail audit) { public AuditTrail Audit { get; } = audit; }

internal sealed class ReportCache(UnitOfWork unitOfWork) { public UnitOfWork UnitOfWork { get; } = unitOfWork; }
