namespace CatalogProxies.Domain;

/// <summary>
/// The subject interface. Every proxy implements it too, so callers can't tell (and needn't
/// care) whether they are talking to the real repository or to a stack of proxies.
/// </summary>
public interface IProductRepository
{
    /// <returns>The product, or <c>null</c> when no product has that id.</returns>
    Task<Product?> GetByIdAsync(ProductId id, CancellationToken cancellationToken = default);

    /// <returns>Products in the category, ordered by id.</returns>
    Task<IReadOnlyList<Product>> ListByCategoryAsync(string category, CancellationToken cancellationToken = default);

    /// <summary>Inserts or replaces the product with the same id.</summary>
    Task SaveAsync(Product product, CancellationToken cancellationToken = default);

    /// <returns><c>true</c> if a product was removed.</returns>
    Task<bool> DeleteAsync(ProductId id, CancellationToken cancellationToken = default);
}
