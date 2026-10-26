using MiniIoC;
using MiniIoC.Demo;

Console.WriteLine("== 1. Lifetimes across two simulated requests ==");

var services = new ServiceCollection()
    .AddSingleton<ConsoleLog>()
    .AddSingleton<IClock, SystemClock>()
    .AddScoped<UnitOfWork>()
    .Add(typeof(IRepository<>), typeof(Repository<>), ServiceLifetime.Scoped)
    .AddTransient<IOrderValidator, PositiveTotalValidator>()
    .AddTransient<IOrderValidator, NotFromTheFutureValidator>()
    .AddTransient<OrderService>();

await using (var container = services.BuildServiceProvider())
{
    var orderNumber = 1;
    foreach (var request in new[] { "request A", "request B" })
    {
        Console.WriteLine($"-- {request}");
        await using var scope = container.CreateScope();
        var provider = scope.ServiceProvider;

        // Two transient OrderServices, but the scoped UnitOfWork/Repository are shared.
        provider.GetRequiredService<OrderService>().Place(new Order(orderNumber++, 42.50m));
        provider.GetRequiredService<OrderService>().Place(new Order(orderNumber++, -1m));
    }
}

Console.WriteLine();
Console.WriteLine("== 2. Diagnostics: problems caught when the container is built ==");

Report(() => new ServiceCollection()
    .AddSingleton<AuditTrail>()
    .AddSingleton<NotificationHub>()
    .BuildServiceProvider());

Report(() => new ServiceCollection()
    .AddSingleton<ConsoleLog>()
    .AddScoped<UnitOfWork>()
    .AddSingleton<ReportCache>()
    .BuildServiceProvider());

Report(() => new ServiceCollection()
    .AddTransient<OrderService>()
    .BuildServiceProvider());

static void Report(Func<Container> build)
{
    try
    {
        using var _ = build();
        Console.WriteLine("  (no problems)");
    }
    catch (ContainerValidationException ex)
    {
        foreach (var error in ex.Errors)
        {
            Console.WriteLine($"  {error.GetType().Name}: {error.Message}");
        }
    }
}
