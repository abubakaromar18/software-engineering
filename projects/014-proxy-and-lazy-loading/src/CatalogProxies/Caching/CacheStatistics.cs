namespace CatalogProxies.Caching;

/// <summary>
/// Counters for a cache.
/// <c>Coalesced</c> counts callers that joined a load already in flight instead of starting their own.
/// </summary>
public readonly record struct CacheStatistics(long Hits, long Misses, long Coalesced, long Evictions, long Invalidations)
{
    public long Requests => Hits + Misses + Coalesced;

    /// <summary>Share of requests that did not start a load (hits and coalesced callers).</summary>
    public double HitRatio => Requests == 0 ? 0 : (double)(Hits + Coalesced) / Requests;

    public static CacheStatistics operator +(CacheStatistics left, CacheStatistics right) => new(
        left.Hits + right.Hits,
        left.Misses + right.Misses,
        left.Coalesced + right.Coalesced,
        left.Evictions + right.Evictions,
        left.Invalidations + right.Invalidations);

    public static CacheStatistics Add(CacheStatistics left, CacheStatistics right) => left + right;
}
