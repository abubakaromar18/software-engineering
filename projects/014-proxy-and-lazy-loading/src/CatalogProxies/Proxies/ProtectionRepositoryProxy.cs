using CatalogProxies.Domain;
using CatalogProxies.Security;

namespace CatalogProxies.Proxies;

/// <summary>
/// <b>Protection proxy.</b> Checks the caller's permissions before forwarding, so the real
/// repository can stay ignorant of users and roles.
/// <list type="bullet">
/// <item>Reads need <see cref="CatalogPermissions.ReadCatalog"/>. Results have <c>CostPrice</c>
/// removed unless the caller also has <see cref="CatalogPermissions.ViewCost"/>.</item>
/// <item>Saves need <see cref="CatalogPermissions.WriteCatalog"/>. A caller who can't see cost prices
/// can't change them either: the stored cost price is kept, whatever they send.</item>
/// <item>Deletes need <see cref="CatalogPermissions.DeleteCatalog"/>.</item>
/// </list>
/// Checks happen before the inner call, so a denied request has no side effects and costs no I/O.
/// </summary>
public sealed class ProtectionRepositoryProxy : IProductRepository
{
    private readonly IProductRepository _inner;
    private readonly IUserContext _user;

    public ProtectionRepositoryProxy(IProductRepository inner, IUserContext user)
    {
        ArgumentNullException.ThrowIfNull(inner);
        ArgumentNullException.ThrowIfNull(user);
        _inner = inner;
        _user = user;
    }

    public async Task<Product?> GetByIdAsync(ProductId id, CancellationToken cancellationToken = default)
    {
        Demand(CatalogPermissions.ReadCatalog, "read the catalog");
        var product = await _inner.GetByIdAsync(id, cancellationToken).ConfigureAwait(false);
        return product is null ? null : Redact(product);
    }

    public async Task<IReadOnlyList<Product>> ListByCategoryAsync(string category, CancellationToken cancellationToken = default)
    {
        Demand(CatalogPermissions.ReadCatalog, "read the catalog");
        var products = await _inner.ListByCategoryAsync(category, cancellationToken).ConfigureAwait(false);
        return _user.Has(CatalogPermissions.ViewCost) ? products : products.Select(Redact).ToList();
    }

    public async Task SaveAsync(Product product, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(product);
        Demand(CatalogPermissions.WriteCatalog, "change the catalog");

        if (!_user.Has(CatalogPermissions.ViewCost))
        {
            // The caller was shown a redacted product, so a null cost price here means
            // "I don't know", not "clear it". Keep whatever is stored.
            var existing = await _inner.GetByIdAsync(product.Id, cancellationToken).ConfigureAwait(false);
            product = product.WithCostPrice(existing?.CostPrice);
        }

        await _inner.SaveAsync(product, cancellationToken).ConfigureAwait(false);
    }

    public Task<bool> DeleteAsync(ProductId id, CancellationToken cancellationToken = default)
    {
        Demand(CatalogPermissions.DeleteCatalog, "delete from the catalog");
        return _inner.DeleteAsync(id, cancellationToken);
    }

    private void Demand(CatalogPermissions permission, string operation)
    {
        if (!_user.Has(permission))
        {
            throw new AccessDeniedException(_user.UserName, permission, operation);
        }
    }

    private Product Redact(Product product) =>
        _user.Has(CatalogPermissions.ViewCost) || product.CostPrice is null ? product : product.WithCostPrice(null);
}
