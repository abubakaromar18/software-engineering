using System.Collections.ObjectModel;
using CatalogProxies.Caching;
using CatalogProxies.Domain;

namespace CatalogProxies.Proxies;

/// <summary>
/// <b>Caching proxy.</b> Serves repeated reads from memory and goes to the inner repository
/// only on a miss, after expiry, or after a write made through this proxy.
/// <para>
/// Invalidation is deliberately coarse: a write drops the product's own entry and <i>every</i>
/// category list, because the product may have moved between categories. That is always
/// correct and cheap to reason about. Writes that bypass this proxy are only picked up after
/// one <see cref="CacheOptions.TimeToLive"/>.
/// </para>
/// </summary>
public sealed class CachingRepositoryProxy : IProductRepository
{
    private readonly IProductRepository _inner;
    private readonly ReadThroughCache<ProductId, Product?> _byId;
    private readonly ReadThroughCache<string, IReadOnlyList<Product>> _byCategory;

    public CachingRepositoryProxy(IProductRepository inner, CacheOptions? options = null, TimeProvider? time = null)
    {
        ArgumentNullException.ThrowIfNull(inner);
        _inner = inner;
        options ??= new CacheOptions();
        time ??= TimeProvider.System;

        _byId = new ReadThroughCache<ProductId, Product?>(
            options, time, shouldCache: product => product is not null || options.CacheMisses);
        _byCategory = new ReadThroughCache<string, IReadOnlyList<Product>>(
            options, time, StringComparer.OrdinalIgnoreCase);
    }

    public CacheStatistics Statistics => _byId.Statistics + _byCategory.Statistics;

    public Task<Product?> GetByIdAsync(ProductId id, CancellationToken cancellationToken = default) =>
        _byId.GetOrLoadAsync(id, ct => _inner.GetByIdAsync(id, ct), cancellationToken);

    public Task<IReadOnlyList<Product>> ListByCategoryAsync(string category, CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(category);
        var key = category.Trim();
        return _byCategory.GetOrLoadAsync(key, ct => LoadCategoryAsync(key, ct), cancellationToken);
    }

    public async Task SaveAsync(Product product, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(product);
        try
        {
            await _inner.SaveAsync(product, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            // Also on failure: we can't know whether the store applied the write before failing.
            InvalidateFor(product.Id);
        }
    }

    public async Task<bool> DeleteAsync(ProductId id, CancellationToken cancellationToken = default)
    {
        try
        {
            return await _inner.DeleteAsync(id, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            InvalidateFor(id);
        }
    }

    /// <summary>Drops everything, e.g. after a bulk import that bypassed this proxy.</summary>
    public void Clear()
    {
        _byId.Clear();
        _byCategory.Clear();
    }

    private async Task<IReadOnlyList<Product>> LoadCategoryAsync(string category, CancellationToken cancellationToken)
    {
        var products = await _inner.ListByCategoryAsync(category, cancellationToken).ConfigureAwait(false);

        // The same list is handed to every caller, so it must not be castable back to a mutable List<T>.
        return new ReadOnlyCollection<Product>(products.ToArray());
    }

    private void InvalidateFor(ProductId id)
    {
        _byId.Invalidate(id);
        _byCategory.Clear();
    }
}
