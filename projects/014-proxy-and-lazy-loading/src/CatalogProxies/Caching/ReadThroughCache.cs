namespace CatalogProxies.Caching;

/// <summary>
/// A small read-through cache with TTL, LRU eviction and single-flight loading.
/// <list type="bullet">
/// <item><b>Single flight.</b> The first caller for a missing key starts the load. Callers
/// that arrive while it runs await the same task, so a burst of identical requests reaches
/// the store once (no cache stampede).</item>
/// <item><b>Failures aren't cached.</b> A failed load is removed so the next caller retries.</item>
/// <item><b>Invalidation wins over in-flight loads.</b> A load only stores its result if its
/// entry is still the current one. If <see cref="Invalidate"/> ran meanwhile (because of a
/// write), the possibly stale result goes to the callers already waiting but is not cached.</item>
/// </list>
/// One lock guards the map and the LRU list. Loads run outside the lock.
/// </summary>
internal sealed class ReadThroughCache<TKey, TValue>
    where TKey : notnull
{
    private readonly object _gate = new();
    private readonly Dictionary<TKey, LinkedListNode<Entry>> _entries;
    private readonly LinkedList<Entry> _recency = new(); // head = most recently used
    private readonly CacheOptions _options;
    private readonly TimeProvider _time;
    private readonly Func<TValue, bool> _shouldCache;

    private long _hits;
    private long _misses;
    private long _coalesced;
    private long _evictions;
    private long _invalidations;

    public ReadThroughCache(
        CacheOptions options,
        TimeProvider time,
        IEqualityComparer<TKey>? comparer = null,
        Func<TValue, bool>? shouldCache = null)
    {
        _options = options;
        _time = time;
        _entries = new Dictionary<TKey, LinkedListNode<Entry>>(comparer);
        _shouldCache = shouldCache ?? (_ => true);
    }

    public int Count
    {
        get
        {
            lock (_gate)
            {
                return _entries.Count;
            }
        }
    }

    public CacheStatistics Statistics
    {
        get
        {
            lock (_gate)
            {
                return new CacheStatistics(_hits, _misses, _coalesced, _evictions, _invalidations);
            }
        }
    }

    /// <summary>
    /// Returns the cached value or loads it. The loader is shared by every waiting caller, so it
    /// gets <see cref="CancellationToken.None"/>; <paramref name="cancellationToken"/> only stops
    /// this caller waiting.
    /// </summary>
    public Task<TValue> GetOrLoadAsync(TKey key, Func<CancellationToken, Task<TValue>> loader, CancellationToken cancellationToken)
    {
        Entry entry;
        var startLoad = false;

        lock (_gate)
        {
            if (_entries.TryGetValue(key, out var node) && IsUsable(node.Value, out var pending))
            {
                if (pending)
                {
                    _coalesced++;
                }
                else
                {
                    _hits++;
                }

                MoveToFront(node);
                entry = node.Value;
            }
            else
            {
                if (node is not null)
                {
                    Remove(node);
                }

                _misses++;
                entry = new Entry(key);
                _entries[key] = _recency.AddFirst(entry);
                startLoad = true;
                EvictOverflow();
            }
        }

        if (startLoad)
        {
            _ = LoadAsync(entry, loader);
        }

        return entry.Completion.Task.WaitAsync(cancellationToken);
    }

    public void Invalidate(TKey key)
    {
        lock (_gate)
        {
            if (_entries.TryGetValue(key, out var node))
            {
                Remove(node);
                _invalidations++;
            }
        }
    }

    public void Clear()
    {
        lock (_gate)
        {
            _invalidations += _entries.Count;
            _entries.Clear();
            _recency.Clear();
        }
    }

    private async Task LoadAsync(Entry entry, Func<CancellationToken, Task<TValue>> loader)
    {
        try
        {
            var value = await loader(CancellationToken.None).ConfigureAwait(false);
            lock (_gate)
            {
                if (IsCurrent(entry, out var node))
                {
                    if (_shouldCache(value))
                    {
                        entry.ExpiresAt = _time.GetUtcNow() + _options.TimeToLive;
                    }
                    else
                    {
                        Remove(node);
                    }
                }
            }

            entry.Completion.SetResult(value);
        }
#pragma warning disable CA1031 // Any failure must reach the waiting callers, whatever its type.
        catch (Exception ex)
#pragma warning restore CA1031
        {
            lock (_gate)
            {
                if (IsCurrent(entry, out var node))
                {
                    Remove(node);
                }
            }

            entry.Completion.SetException(ex);
        }
    }

    private bool IsUsable(Entry entry, out bool pending)
    {
        pending = entry.ExpiresAt is null;
        return pending || entry.ExpiresAt > _time.GetUtcNow();
    }

    private bool IsCurrent(Entry entry, out LinkedListNode<Entry> node) =>
        _entries.TryGetValue(entry.Key, out node!) && ReferenceEquals(node.Value, entry);

    private void MoveToFront(LinkedListNode<Entry> node)
    {
        _recency.Remove(node);
        _recency.AddFirst(node);
    }

    private void Remove(LinkedListNode<Entry> node)
    {
        _entries.Remove(node.Value.Key);
        _recency.Remove(node);
    }

    private void EvictOverflow()
    {
        while (_entries.Count > _options.MaxEntries && _recency.Last is { } oldest)
        {
            Remove(oldest);
            _evictions++;
        }
    }

    private sealed class Entry(TKey key)
    {
        public TKey Key { get; } = key;

        public TaskCompletionSource<TValue> Completion { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);

        /// <summary>Null while the load is still running.</summary>
        public DateTimeOffset? ExpiresAt { get; set; }
    }
}
