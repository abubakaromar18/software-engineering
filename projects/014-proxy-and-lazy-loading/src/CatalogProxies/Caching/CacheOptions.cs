namespace CatalogProxies.Caching;

/// <summary>Settings for <see cref="Proxies.CachingRepositoryProxy"/>.</summary>
public sealed record CacheOptions
{
    private readonly TimeSpan _timeToLive = TimeSpan.FromSeconds(30);
    private readonly int _maxEntries = 1024;

    /// <summary>How long a loaded value is served before it is fetched again. Measured from when the load finishes.</summary>
    public TimeSpan TimeToLive
    {
        get => _timeToLive;
        init
        {
            ArgumentOutOfRangeException.ThrowIfLessThanOrEqual(value, TimeSpan.Zero);
            _timeToLive = value;
        }
    }

    /// <summary>Upper bound per cache. The least recently used entry is evicted first.</summary>
    public int MaxEntries
    {
        get => _maxEntries;
        init
        {
            ArgumentOutOfRangeException.ThrowIfLessThan(value, 1);
            _maxEntries = value;
        }
    }

    /// <summary>
    /// Also cache "not found" results (negative caching). Protects the store from repeated
    /// lookups of ids that don't exist, at the price of a new product staying invisible
    /// for up to one TTL if it was created by someone who bypasses this proxy.
    /// </summary>
    public bool CacheMisses { get; init; } = true;
}
