package cache

import (
	"fmt"
	"math/rand/v2"
	"slices"
	"testing"
)

// The O(1) caches are checked against deliberately naive O(n) models whose
// correctness is obvious by inspection: every entry carries the logical time
// of its last access (and, for LFU, its access count), and eviction scans for
// the minimum. If the fast and slow versions agree on every operation of a
// long random sequence, the pointer juggling is almost certainly right.

type modelEntry struct {
	value    int
	freq     uint64
	lastUsed uint64
}

type model struct {
	capacity int
	lfu      bool
	clock    uint64
	items    map[int]*modelEntry
	evicted  []int
}

func newModel(capacity int, lfu bool) *model {
	return &model{capacity: capacity, lfu: lfu, items: map[int]*modelEntry{}}
}

func (m *model) access(e *modelEntry) {
	m.clock++
	e.lastUsed = m.clock
	e.freq++
}

func (m *model) get(k int) (int, bool) {
	e, ok := m.items[k]
	if !ok {
		return 0, false
	}
	m.access(e)
	return e.value, true
}

func (m *model) put(k, v int) bool {
	if e, ok := m.items[k]; ok {
		e.value = v
		m.access(e)
		return false
	}
	evicted := false
	if len(m.items) >= m.capacity {
		m.evict()
		evicted = true
	}
	e := &modelEntry{value: v}
	m.access(e)
	m.items[k] = e
	return evicted
}

// worse reports whether a should be evicted in preference to b.
func (m *model) worse(a, b *modelEntry) bool {
	if m.lfu && a.freq != b.freq {
		return a.freq < b.freq
	}
	return a.lastUsed < b.lastUsed
}

func (m *model) evict() {
	victim, first := 0, true
	for k, e := range m.items {
		if first || m.worse(e, m.items[victim]) {
			victim, first = k, false
		}
	}
	delete(m.items, victim)
	m.evicted = append(m.evicted, victim)
}

// op is one step of a generated workload.
type op struct {
	kind byte // 0 get, 1 put, 2 delete, 3 peek
	key  int
	val  int
}

// checkAgainstModel runs ops on a fresh cache and its model, failing on the
// first divergence. Keys come from a small range so hits and evictions are
// frequent.
func checkAgainstModel(t *testing.T, lfu bool, capacity int, ops []op) {
	t.Helper()
	m := newModel(capacity, lfu)
	var evicted []int
	onEvict := WithOnEvict(func(k, _ int) { evicted = append(evicted, k) })

	var c interface {
		Cache[int, int]
		Keys() []int
	}
	if lfu {
		c = mustLFU(t, capacity, onEvict)
	} else {
		c = mustLRU(t, capacity, onEvict)
	}

	for i, o := range ops {
		switch o.kind {
		case 0:
			gv, gok := c.Get(o.key)
			wv, wok := m.get(o.key)
			if gv != wv || gok != wok {
				t.Fatalf("op %d Get(%d) = %d,%v; model %d,%v", i, o.key, gv, gok, wv, wok)
			}
		case 1:
			if got, want := c.Put(o.key, o.val), m.put(o.key, o.val); got != want {
				t.Fatalf("op %d Put(%d) evicted=%v; model %v", i, o.key, got, want)
			}
		case 2:
			_, want := m.items[o.key]
			delete(m.items, o.key)
			if got := c.Delete(o.key); got != want {
				t.Fatalf("op %d Delete(%d) = %v; model %v", i, o.key, got, want)
			}
		case 3:
			gv, gok := c.Peek(o.key)
			e, wok := m.items[o.key]
			if gok != wok || (wok && gv != e.value) {
				t.Fatalf("op %d Peek(%d) = %d,%v; model present=%v", i, o.key, gv, gok, wok)
			}
		}
		if c.Len() != len(m.items) {
			t.Fatalf("op %d Len = %d; model %d", i, c.Len(), len(m.items))
		}
		if !slices.Equal(evicted, m.evicted) {
			t.Fatalf("op %d evicted %v; model %v", i, evicted, m.evicted)
		}
	}
	if got := len(c.Keys()); got != c.Len() {
		t.Fatalf("Keys has %d entries, Len %d", got, c.Len())
	}
}

func randomOps(r *rand.Rand, n, keySpace int) []op {
	ops := make([]op, n)
	for i := range ops {
		// Weighted towards Get/Put so the caches stay full and busy.
		kind := byte(0)
		switch x := r.IntN(10); {
		case x < 4:
			kind = 0
		case x < 8:
			kind = 1
		case x < 9:
			kind = 2
		default:
			kind = 3
		}
		ops[i] = op{kind: kind, key: r.IntN(keySpace), val: r.Int()}
	}
	return ops
}

func TestCachesMatchModel(t *testing.T) {
	for _, policy := range []struct {
		name string
		lfu  bool
	}{{"LRU", false}, {"LFU", true}} {
		for _, capacity := range []int{1, 2, 5, 16} {
			t.Run(fmt.Sprintf("%s/cap=%d", policy.name, capacity), func(t *testing.T) {
				r := rand.New(rand.NewPCG(uint64(capacity), 42))
				checkAgainstModel(t, policy.lfu, capacity, randomOps(r, 5000, 3*capacity+2))
			})
		}
	}
}

// FuzzCachesMatchModel lets `go test -fuzz` search for op sequences on which
// either cache disagrees with its model. Each input byte encodes one op.
// Without -fuzz, the seed corpus below runs as an ordinary test.
func FuzzCachesMatchModel(f *testing.F) {
	f.Add(uint8(2), []byte{0x40, 0x41, 0x42, 0x01, 0x43, 0x80})
	f.Add(uint8(1), []byte{0x40, 0x40, 0x41, 0x00, 0xC0})
	f.Add(uint8(4), []byte("put-get-delete-peek mixed bytes"))
	f.Fuzz(func(t *testing.T, capacity uint8, data []byte) {
		capN := int(capacity%8) + 1
		ops := make([]op, len(data))
		for i, b := range data {
			// top two bits: op kind; low bits: key in a small range.
			ops[i] = op{kind: b >> 6, key: int(b&0x3F) % (2*capN + 3), val: i}
		}
		checkAgainstModel(t, false, capN, ops)
		checkAgainstModel(t, true, capN, ops)
	})
}
