using CatalogProxies.Domain;
using CatalogProxies.Lazy;

namespace CatalogProxies.Proxies;

/// <summary>
/// <b>Virtual proxy.</b> Stands in for a repository that is expensive to create and creates it
/// on the first call that actually needs it. Applications that start up, register this, and
/// never touch the catalog never pay the connection cost.
/// </summary>
public sealed class VirtualRepositoryProxy : IProductRepository, IAsyncDisposable
{
    private readonly AsyncLazy<IProductRepository> _subject;

    public VirtualRepositoryProxy(Func<CancellationToken, Task<IProductRepository>> connect)
    {
        ArgumentNullException.ThrowIfNull(connect);
        _subject = new AsyncLazy<IProductRepository>(connect);
    }

    /// <summary>Whether the real repository has been created yet.</summary>
    public bool IsMaterialized => _subject.IsValueCreated;

    public async Task<Product?> GetByIdAsync(ProductId id, CancellationToken cancellationToken = default) =>
        await (await Subject(cancellationToken).ConfigureAwait(false))
            .GetByIdAsync(id, cancellationToken).ConfigureAwait(false);

    public async Task<IReadOnlyList<Product>> ListByCategoryAsync(string category, CancellationToken cancellationToken = default) =>
        await (await Subject(cancellationToken).ConfigureAwait(false))
            .ListByCategoryAsync(category, cancellationToken).ConfigureAwait(false);

    public async Task SaveAsync(Product product, CancellationToken cancellationToken = default) =>
        await (await Subject(cancellationToken).ConfigureAwait(false))
            .SaveAsync(product, cancellationToken).ConfigureAwait(false);

    public async Task<bool> DeleteAsync(ProductId id, CancellationToken cancellationToken = default) =>
        await (await Subject(cancellationToken).ConfigureAwait(false))
            .DeleteAsync(id, cancellationToken).ConfigureAwait(false);

    /// <summary>Disposes the real subject, but only if it was ever created.</summary>
    public async ValueTask DisposeAsync()
    {
        if (!_subject.TryGetValue(out var subject))
        {
            return;
        }

        switch (subject)
        {
            case IAsyncDisposable asyncDisposable:
                await asyncDisposable.DisposeAsync().ConfigureAwait(false);
                break;
            case IDisposable disposable:
                disposable.Dispose();
                break;
        }
    }

    private Task<IProductRepository> Subject(CancellationToken cancellationToken) =>
        _subject.GetValueAsync(cancellationToken);
}
