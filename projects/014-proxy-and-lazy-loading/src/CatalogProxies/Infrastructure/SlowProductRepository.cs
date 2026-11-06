using System.Collections.Concurrent;
using CatalogProxies.Domain;

namespace CatalogProxies.Infrastructure;

/// <summary>
/// The real subject: an in-memory store that behaves like a remote one. Connecting is
/// expensive (it "warms up" an index) and every call pays <see cref="ILatency"/>.
/// </summary>
public sealed class SlowProductRepository : IProductRepository
{
    private readonly ConcurrentDictionary<ProductId, Product> _products = new();
    private readonly ILatency _callLatency;

    private SlowProductRepository(ILatency callLatency, IEnumerable<Product> seed)
    {
        _callLatency = callLatency;
        foreach (var product in seed)
        {
            _products[product.Id] = product;
        }
    }

    /// <summary>Creates the repository after paying the one-off connection cost.</summary>
    public static async Task<SlowProductRepository> ConnectAsync(
        IEnumerable<Product> seed,
        ILatency connectLatency,
        ILatency callLatency,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(seed);
        ArgumentNullException.ThrowIfNull(connectLatency);
        ArgumentNullException.ThrowIfNull(callLatency);

        await connectLatency.WaitAsync(cancellationToken).ConfigureAwait(false);
        return new SlowProductRepository(callLatency, seed);
    }

    public async Task<Product?> GetByIdAsync(ProductId id, CancellationToken cancellationToken = default)
    {
        await _callLatency.WaitAsync(cancellationToken).ConfigureAwait(false);
        return _products.TryGetValue(id, out var product) ? product : null;
    }

    public async Task<IReadOnlyList<Product>> ListByCategoryAsync(string category, CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(category);
        await _callLatency.WaitAsync(cancellationToken).ConfigureAwait(false);
        return _products.Values
            .Where(p => string.Equals(p.Category, category.Trim(), StringComparison.OrdinalIgnoreCase))
            .OrderBy(p => p.Id.Value, StringComparer.Ordinal)
            .ToList();
    }

    public async Task SaveAsync(Product product, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(product);
        await _callLatency.WaitAsync(cancellationToken).ConfigureAwait(false);
        _products[product.Id] = product;
    }

    public async Task<bool> DeleteAsync(ProductId id, CancellationToken cancellationToken = default)
    {
        await _callLatency.WaitAsync(cancellationToken).ConfigureAwait(false);
        return _products.TryRemove(id, out _);
    }
}
