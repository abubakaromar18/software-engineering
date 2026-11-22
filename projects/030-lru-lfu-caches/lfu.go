package cache

import "github.com/abubakaromar18/software-engineering/projects/030-lru-lfu-caches/internal/dlist"

// LFU is a least-frequently-used cache with O(1) Get, Put and Delete.
//
// Entries are grouped into frequency buckets. Buckets form a list sorted by
// ascending access count, and each bucket holds its entries in recency order:
//
//	buckets:  [freq 1] <-> [freq 3] <-> [freq 7]
//	             |            |            |
//	           e  d          b  c          a      (front = most recent)
//
// An access moves an entry from bucket f to bucket f+1, which is either the
// next bucket or a new one inserted right after it, so no search is needed.
// Eviction takes the back (least recent) entry of the first (lowest
// frequency) bucket. Empty buckets are unlinked immediately, which is what
// keeps Delete O(1): there is no "minimum frequency" field to recompute.
//
// Both Get and Put on an existing key count as an access. LFU is not safe for
// concurrent use; see Synchronized and Sharded.
type LFU[K comparable, V any] struct {
	capacity int
	items    map[K]*dlist.Node[lfuEntry[K, V]]
	buckets  dlist.List[bucket[K, V]]
	cfg      config[K, V]
	stats    Stats
}

type lfuEntry[K comparable, V any] struct {
	key    K
	value  V
	bucket *dlist.Node[bucket[K, V]] // the bucket whose list holds this entry
}

type bucket[K comparable, V any] struct {
	freq    uint64
	entries dlist.List[lfuEntry[K, V]]
}

var _ Cache[string, int] = (*LFU[string, int])(nil)

// NewLFU returns an empty LFU holding at most capacity entries.
func NewLFU[K comparable, V any](capacity int, opts ...Option[K, V]) (*LFU[K, V], error) {
	cfg, err := buildConfig(capacity, opts)
	if err != nil {
		return nil, err
	}
	return &LFU[K, V]{
		capacity: capacity,
		items:    make(map[K]*dlist.Node[lfuEntry[K, V]], capacity),
		cfg:      cfg,
	}, nil
}

// Get returns the value for key and increments its access count.
func (c *LFU[K, V]) Get(key K) (V, bool) {
	n, ok := c.items[key]
	if !ok {
		c.stats.Misses++
		var zero V
		return zero, false
	}
	c.stats.Hits++
	c.touch(n)
	return n.Value.value, true
}

// Peek returns the value for key without changing its count or stats.
func (c *LFU[K, V]) Peek(key K) (V, bool) {
	if n, ok := c.items[key]; ok {
		return n.Value.value, true
	}
	var zero V
	return zero, false
}

// Put inserts key with an access count of 1, or updates an existing key and
// increments its count. If the cache is full and key is new, the least
// frequently used entry (least recent among ties) is evicted first.
func (c *LFU[K, V]) Put(key K, value V) bool {
	if n, ok := c.items[key]; ok {
		n.Value.value = value
		c.touch(n)
		return false
	}
	evicted := false
	if len(c.items) >= c.capacity {
		c.evict()
		evicted = true
	}
	first := c.buckets.Front()
	if first == nil || first.Value.freq != 1 {
		first = c.buckets.PushFront(bucket[K, V]{freq: 1})
	}
	c.items[key] = first.Value.entries.PushFront(lfuEntry[K, V]{key: key, value: value, bucket: first})
	return evicted
}

// Delete removes key and reports whether it was present.
func (c *LFU[K, V]) Delete(key K) bool {
	n, ok := c.items[key]
	if !ok {
		return false
	}
	c.unlink(n)
	delete(c.items, key)
	return true
}

// touch promotes n from its bucket (freq f) to the bucket for f+1.
func (c *LFU[K, V]) touch(n *dlist.Node[lfuEntry[K, V]]) {
	cur := n.Value.bucket
	want := cur.Value.freq + 1

	next := cur.Next()
	if next == nil || next.Value.freq != want {
		// Insert before unlinking n so cur is still a valid anchor even if it
		// is about to become empty and be removed.
		next = c.buckets.InsertAfter(bucket[K, V]{freq: want}, cur)
	}
	c.unlink(n)
	next.Value.entries.PushNodeFront(n)
	n.Value.bucket = next
}

// unlink detaches n from its bucket and drops the bucket if it became empty.
func (c *LFU[K, V]) unlink(n *dlist.Node[lfuEntry[K, V]]) {
	b := n.Value.bucket
	b.Value.entries.Remove(n)
	if b.Value.entries.Len() == 0 {
		c.buckets.Remove(b)
	}
	n.Value.bucket = nil
}

func (c *LFU[K, V]) evict() {
	victim := c.buckets.Front().Value.entries.Back()
	key, value := victim.Value.key, victim.Value.value
	c.unlink(victim)
	delete(c.items, key)
	c.stats.Evictions++
	if c.cfg.onEvict != nil {
		c.cfg.onEvict(key, value)
	}
}

// Frequency returns key's access count without recording an access.
func (c *LFU[K, V]) Frequency(key K) (uint64, bool) {
	n, ok := c.items[key]
	if !ok {
		return 0, false
	}
	return n.Value.bucket.Value.freq, true
}

// Len returns the number of stored entries.
func (c *LFU[K, V]) Len() int { return len(c.items) }

// Cap returns the maximum number of entries.
func (c *LFU[K, V]) Cap() int { return c.capacity }

// Stats returns a snapshot of the counters.
func (c *LFU[K, V]) Stats() Stats { return c.stats }

// Keys returns keys in reverse eviction order: highest frequency first, most
// recent first within a frequency. The last key is evicted next.
func (c *LFU[K, V]) Keys() []K {
	keys := make([]K, 0, len(c.items))
	for b := c.buckets.Back(); b != nil; b = b.Prev() {
		for n := b.Value.entries.Front(); n != nil; n = n.Next() {
			keys = append(keys, n.Value.key)
		}
	}
	return keys
}
