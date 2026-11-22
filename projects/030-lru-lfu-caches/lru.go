package cache

import "github.com/abubakaromar18/software-engineering/projects/030-lru-lfu-caches/internal/dlist"

type entry[K comparable, V any] struct {
	key   K
	value V
}

// LRU is a least-recently-used cache. A hash map gives O(1) lookup of a list
// node; the list keeps entries ordered from most recently used (front) to
// least recently used (back), so promotion and eviction are O(1) pointer
// swaps.
//
// LRU is not safe for concurrent use; see Synchronized and Sharded.
type LRU[K comparable, V any] struct {
	capacity int
	items    map[K]*dlist.Node[entry[K, V]]
	order    dlist.List[entry[K, V]]
	cfg      config[K, V]
	stats    Stats
}

var _ Cache[string, int] = (*LRU[string, int])(nil)

// NewLRU returns an empty LRU holding at most capacity entries.
func NewLRU[K comparable, V any](capacity int, opts ...Option[K, V]) (*LRU[K, V], error) {
	cfg, err := buildConfig(capacity, opts)
	if err != nil {
		return nil, err
	}
	return &LRU[K, V]{
		capacity: capacity,
		items:    make(map[K]*dlist.Node[entry[K, V]], capacity),
		cfg:      cfg,
	}, nil
}

// Get returns the value for key and marks it most recently used.
func (c *LRU[K, V]) Get(key K) (V, bool) {
	n, ok := c.items[key]
	if !ok {
		c.stats.Misses++
		var zero V
		return zero, false
	}
	c.stats.Hits++
	c.order.MoveToFront(n)
	return n.Value.value, true
}

// Peek returns the value for key without changing recency or stats.
func (c *LRU[K, V]) Peek(key K) (V, bool) {
	if n, ok := c.items[key]; ok {
		return n.Value.value, true
	}
	var zero V
	return zero, false
}

// Put inserts or updates key and marks it most recently used. If the cache is
// full and key is new, the least recently used entry is evicted first.
func (c *LRU[K, V]) Put(key K, value V) bool {
	if n, ok := c.items[key]; ok {
		n.Value.value = value
		c.order.MoveToFront(n)
		return false
	}
	evicted := false
	if len(c.items) >= c.capacity {
		c.evict()
		evicted = true
	}
	c.items[key] = c.order.PushFront(entry[K, V]{key: key, value: value})
	return evicted
}

// Delete removes key and reports whether it was present.
func (c *LRU[K, V]) Delete(key K) bool {
	n, ok := c.items[key]
	if !ok {
		return false
	}
	c.order.Remove(n)
	delete(c.items, key)
	return true
}

func (c *LRU[K, V]) evict() {
	victim := c.order.Back()
	c.order.Remove(victim)
	delete(c.items, victim.Value.key)
	c.stats.Evictions++
	if c.cfg.onEvict != nil {
		c.cfg.onEvict(victim.Value.key, victim.Value.value)
	}
}

// Len returns the number of stored entries.
func (c *LRU[K, V]) Len() int { return len(c.items) }

// Cap returns the maximum number of entries.
func (c *LRU[K, V]) Cap() int { return c.capacity }

// Stats returns a snapshot of the counters.
func (c *LRU[K, V]) Stats() Stats { return c.stats }

// Keys returns keys from most to least recently used (last is evicted next).
func (c *LRU[K, V]) Keys() []K {
	keys := make([]K, 0, len(c.items))
	for n := c.order.Front(); n != nil; n = n.Next() {
		keys = append(keys, n.Value.key)
	}
	return keys
}
