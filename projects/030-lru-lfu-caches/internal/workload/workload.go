// Package workload generates synthetic, reproducible key streams for comparing
// cache eviction policies. Each workload is designed to expose a strength or
// weakness of LRU or LFU; see the package README section "Choosing a policy".
package workload

import (
	"fmt"
	"math/rand/v2"
	"slices"
	"strings"

	cache "github.com/abubakaromar18/software-engineering/projects/030-lru-lfu-caches"
)

// Generator yields an endless stream of keys in [0, Keys).
type Generator interface {
	Next() int
}

// Spec describes a workload. Zero fields are replaced by defaults in New.
type Spec struct {
	Name string  // one of Names()
	Keys int     // size of the key universe
	Seed uint64  // PRNG seed; the same Spec always yields the same stream
	Skew float64 // Zipf exponent s > 1; larger means a smaller hot set
}

const (
	defaultSkew = 1.1
	// scanEvery and scanLength shape the scan-mix workload: after every
	// scanEvery popular requests comes a burst of scanLength one-off keys.
	scanEvery  = 200
	scanLength = 100
	// shiftEvery is how many requests pass before the shift workload moves its
	// hot set to a different region of the key space.
	shiftEvery = 20_000
)

var constructors = map[string]func(Spec, *rand.Rand) Generator{
	"zipf":     newZipf,
	"loop":     func(s Spec, _ *rand.Rand) Generator { return &loop{keys: s.Keys} },
	"scan-mix": newScanMix,
	"shift":    newShift,
}

// Names lists the available workloads in sorted order.
func Names() []string {
	names := make([]string, 0, len(constructors))
	for n := range constructors {
		names = append(names, n)
	}
	slices.Sort(names)
	return names
}

// New builds the generator described by spec.
func New(spec Spec) (Generator, error) {
	ctor, ok := constructors[spec.Name]
	if !ok {
		return nil, fmt.Errorf("unknown workload %q (want one of %s)", spec.Name, strings.Join(Names(), ", "))
	}
	if spec.Keys < 2 {
		return nil, fmt.Errorf("workload needs at least 2 keys (got %d)", spec.Keys)
	}
	if spec.Skew == 0 {
		spec.Skew = defaultSkew
	}
	if spec.Skew <= 1 {
		return nil, fmt.Errorf("zipf skew must be > 1 (got %g)", spec.Skew)
	}
	return ctor(spec, rand.New(rand.NewPCG(spec.Seed, spec.Seed^0x9E3779B97F4A7C15))), nil
}

// Replay drives c with ops requests from g using the read-through pattern
// most caches see in practice: Get, and on a miss Put the "loaded" value.
func Replay(c cache.Cache[int, int], g Generator, ops int) cache.Stats {
	for range ops {
		k := g.Next()
		if _, ok := c.Get(k); !ok {
			c.Put(k, k)
		}
	}
	return c.Stats()
}

// zipf: a stable popularity distribution, the "normal" case for most caches.
type zipf struct{ z *rand.Zipf }

func newZipf(s Spec, r *rand.Rand) Generator {
	return zipf{z: rand.NewZipf(r, s.Skew, 1, uint64(s.Keys-1))}
}

func (g zipf) Next() int { return int(g.z.Uint64()) }

// loop: 0, 1, ..., Keys-1, 0, 1, ... A cyclic scan larger than the cache is
// LRU's worst case: every key is evicted just before it is needed again.
type loop struct{ keys, i int }

func (g *loop) Next() int {
	k := g.i
	g.i = (g.i + 1) % g.keys
	return k
}

// scanMix: Zipf traffic over the lower half of the keys, interrupted by
// bursts of sequential one-off keys from the upper half (think a batch job or
// crawler walking the catalogue). The scan pollutes LRU; LFU ignores it
// because scanned keys never get past frequency 1.
type scanMix struct {
	hot      zipf
	half     int
	n        int
	scanNext int
}

func newScanMix(s Spec, r *rand.Rand) Generator {
	half := s.Keys / 2
	return &scanMix{hot: zipf{z: rand.NewZipf(r, s.Skew, 1, uint64(half-1))}, half: half}
}

func (g *scanMix) Next() int {
	pos := g.n % (scanEvery + scanLength)
	g.n++
	if pos < scanEvery {
		return g.hot.Next()
	}
	k := g.half + g.scanNext
	g.scanNext = (g.scanNext + 1) % g.half
	return k
}

// shift: Zipf traffic whose hot set jumps to a new region every shiftEvery
// requests (yesterday's news, last season's products). LFU keeps the old
// favourites because their counts are high; LRU adapts immediately.
type shift struct {
	hot  zipf
	keys int
	n    int
}

func newShift(s Spec, r *rand.Rand) Generator { return &shift{hot: newZipf(s, r).(zipf), keys: s.Keys} }

func (g *shift) Next() int {
	phase := g.n / shiftEvery
	g.n++
	// Rotate by a large odd stride so consecutive phases share no hot keys.
	return (g.hot.Next() + phase*(g.keys/3+1)) % g.keys
}
