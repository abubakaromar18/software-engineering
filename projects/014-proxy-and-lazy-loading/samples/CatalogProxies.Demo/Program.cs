// Walks through the proxy chain against a deliberately slow repository and prints what each
// layer did. Run with: dotnet run --project samples/CatalogProxies.Demo
using System.Globalization;
using CatalogProxies;
using CatalogProxies.Caching;
using CatalogProxies.Domain;
using CatalogProxies.Dynamic;
using CatalogProxies.Infrastructure;
using CatalogProxies.Security;

var seed = new[]
{
    new Product(new ProductId("KB-100"), "Mechanical keyboard", "Peripherals", 129m, 61m),
    new Product(new ProductId("MS-200"), "Wireless mouse", "Peripherals", 49m, 18m),
    new Product(new ProductId("DK-300"), "Standing desk", "Furniture", 599m, 310m),
};

var sink = new ConsoleSink();
await using var catalog = new CatalogComposition(
    connect: async ct => await SlowProductRepository.ConnectAsync(
        seed,
        connectLatency: new FixedLatency(TimeSpan.FromMilliseconds(800)),
        callLatency: new FixedLatency(TimeSpan.FromMilliseconds(150)),
        ct),
    cacheOptions: new CacheOptions { TimeToLive = TimeSpan.FromMinutes(5) },
    sink: sink);

var shopper = catalog.ForUser(new StaticUserContext("sam", CatalogPermissions.ReadCatalog));
var admin = catalog.ForUser(new StaticUserContext("ada", CatalogPermissions.ReadCatalog | CatalogPermissions.ViewCost | CatalogPermissions.WriteCatalog));
var keyboard = new ProductId("KB-100");

Section("Virtual proxy: nothing is connected until the first real call");
Console.WriteLine($"  connected: {catalog.IsConnected}");
Show("sam", await shopper.GetByIdAsync(keyboard));
Console.WriteLine($"  connected: {catalog.IsConnected}");

Section("Caching proxy: the same read again is served from memory");
Show("sam", await shopper.GetByIdAsync(keyboard));

Section("Protection proxy: one shared cache, a different view per user");
Show("ada", await admin.GetByIdAsync(keyboard));

Section("Single flight: 10 concurrent reads of an uncached category reach the store once");
await Task.WhenAll(Enumerable.Range(0, 10).Select(_ => shopper.ListByCategoryAsync("Peripherals")));

Section("Writes invalidate, and denied calls never reach the store");
await admin.SaveAsync(new Product(keyboard, "Mechanical keyboard", "Peripherals", 119m, 61m));
Show("sam", await shopper.GetByIdAsync(keyboard));
try
{
    await shopper.SaveAsync(new Product(keyboard, "Hacked", "Peripherals", 1m));
}
catch (AccessDeniedException ex)
{
    Console.WriteLine($"  denied: {ex.Message}");
}

Section("Cache statistics");
Console.WriteLine($"  {catalog.CacheStatistics}");
Console.WriteLine($"  hit ratio: {catalog.CacheStatistics.HitRatio:P0}");

static void Section(string title) => Console.WriteLine($"{Environment.NewLine}== {title}");

static void Show(string user, Product? product) =>
    Console.WriteLine($"  {user} sees {product?.Name} at {Money(product?.Price)}, cost {Money(product?.CostPrice)}");

static string Money(decimal? amount) =>
    amount is { } value ? value.ToString("$0.00", CultureInfo.InvariantCulture) : "hidden";

/// <summary>Prints each call the timing proxy reports.</summary>
internal sealed class ConsoleSink : IInvocationSink
{
    private readonly object _gate = new();

    public void Record(InvocationRecord invocation)
    {
        lock (_gate)
        {
            Console.WriteLine($"  [timing] {invocation.Method,-20} {invocation.Elapsed.TotalMilliseconds,7:0} ms  {invocation.Outcome}");
        }
    }
}
