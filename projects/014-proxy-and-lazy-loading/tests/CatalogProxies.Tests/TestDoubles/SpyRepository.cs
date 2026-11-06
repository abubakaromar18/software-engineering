using System.Collections.Concurrent;
using CatalogProxies.Domain;

namespace CatalogProxies.Tests.TestDoubles;

/// <summary>
/// An in-memory repository that counts calls and can be held or made to fail,
/// so tests can observe exactly what reaches the store.
/// </summary>
public sealed class SpyRepository : IProductRepository
{
    private readonly ConcurrentDictionary<ProductId, Product> _products = new();
    private readonly ConcurrentDictionary<string, int> _calls = new();

    public SpyRepository(params Product[] seed)
    {
        foreach (var product in seed)
        {
            _products[product.Id] = product;
        }
    }

    /// <summary>Awaited at the start of every call. Use it to hold calls open or to throw.</summary>
    public Func<string, Task>? BeforeCall { get; set; }

    public int Calls(string method) => _calls.GetValueOrDefault(method);

    public int TotalCalls => _calls.Values.Sum();

    public Product? Stored(ProductId id) => _products.GetValueOrDefault(id);

    public async Task<Product?> GetByIdAsync(ProductId id, CancellationToken cancellationToken = default)
    {
        await Enter(nameof(GetByIdAsync));
        return _products.GetValueOrDefault(id);
    }

    public async Task<IReadOnlyList<Product>> ListByCategoryAsync(string category, CancellationToken cancellationToken = default)
    {
        await Enter(nameof(ListByCategoryAsync));
        return _products.Values
            .Where(p => string.Equals(p.Category, category, StringComparison.OrdinalIgnoreCase))
            .OrderBy(p => p.Id.Value, StringComparer.Ordinal)
            .ToList();
    }

    public async Task SaveAsync(Product product, CancellationToken cancellationToken = default)
    {
        await Enter(nameof(SaveAsync));
        _products[product.Id] = product;
    }

    public async Task<bool> DeleteAsync(ProductId id, CancellationToken cancellationToken = default)
    {
        await Enter(nameof(DeleteAsync));
        return _products.TryRemove(id, out _);
    }

    private async Task Enter(string method)
    {
        _calls.AddOrUpdate(method, 1, (_, n) => n + 1);
        if (BeforeCall is { } hook)
        {
            await hook(method);
        }
    }
}

/// <summary>A repository that records whether it was disposed.</summary>
public sealed class DisposableRepository : IProductRepository, IAsyncDisposable
{
    private readonly SpyRepository _inner = new();

    public bool Disposed { get; private set; }

    public Task<Product?> GetByIdAsync(ProductId id, CancellationToken cancellationToken = default) => _inner.GetByIdAsync(id, cancellationToken);

    public Task<IReadOnlyList<Product>> ListByCategoryAsync(string category, CancellationToken cancellationToken = default) => _inner.ListByCategoryAsync(category, cancellationToken);

    public Task SaveAsync(Product product, CancellationToken cancellationToken = default) => _inner.SaveAsync(product, cancellationToken);

    public Task<bool> DeleteAsync(ProductId id, CancellationToken cancellationToken = default) => _inner.DeleteAsync(id, cancellationToken);

    public ValueTask DisposeAsync()
    {
        Disposed = true;
        return ValueTask.CompletedTask;
    }
}
