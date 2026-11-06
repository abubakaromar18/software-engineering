using System.Diagnostics.CodeAnalysis;
using CatalogProxies.Caching;
using CatalogProxies.Domain;
using CatalogProxies.Dynamic;
using CatalogProxies.Proxies;
using CatalogProxies.Security;

namespace CatalogProxies;

/// <summary>
/// Composition root for the proxy chain. The order is fixed here, on purpose:
/// <code>
///   per request: Timing ─▶ Protection ─┐
///   shared:                            └─▶ Caching ─▶ Virtual ─▶ real repository
/// </code>
/// <list type="bullet">
/// <item><b>Protection outside caching.</b> The cache is shared by all users and holds
/// unredacted products. CatalogPermissions checks and redaction happen on the way out, per user.
/// The other way round, the first user to load a product would decide what everyone sees.</item>
/// <item><b>Caching outside virtual.</b> Cache hits never force the real repository into existence.</item>
/// <item><b>Timing outermost.</b> It measures what the caller experiences, including hits
/// and denied requests.</item>
/// </list>
/// </summary>
public sealed class CatalogComposition : IAsyncDisposable
{
    private readonly VirtualRepositoryProxy _virtual;
    private readonly CachingRepositoryProxy _cache;
    private readonly IInvocationSink? _sink;
    private readonly TimeProvider _time;

    public CatalogComposition(
        Func<CancellationToken, Task<IProductRepository>> connect,
        CacheOptions? cacheOptions = null,
        IInvocationSink? sink = null,
        TimeProvider? time = null)
    {
        _time = time ?? TimeProvider.System;
        _sink = sink;
        _virtual = new VirtualRepositoryProxy(connect);
        _cache = new CachingRepositoryProxy(_virtual, cacheOptions, _time);
    }

    /// <summary>Whether the real repository has been connected yet.</summary>
    public bool IsConnected => _virtual.IsMaterialized;

    public CacheStatistics CacheStatistics => _cache.Statistics;

    /// <summary>The repository a single user (or request) should use.</summary>
    [RequiresDynamicCode("The timing proxy is generated with DispatchProxy.")]
    public IProductRepository ForUser(IUserContext user)
    {
        IProductRepository repository = new ProtectionRepositoryProxy(_cache, user);
        return _sink is null ? repository : TimingProxy.Create(repository, _sink, _time);
    }

    public ValueTask DisposeAsync() => _virtual.DisposeAsync();
}
