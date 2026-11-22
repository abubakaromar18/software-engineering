package workload

import (
	"slices"
	"testing"

	cache "github.com/abubakaromar18/software-engineering/projects/030-lru-lfu-caches"
)

func take(g Generator, n int) []int {
	out := make([]int, n)
	for i := range out {
		out[i] = g.Next()
	}
	return out
}

func TestNewValidates(t *testing.T) {
	bad := []Spec{
		{Name: "nope", Keys: 10},
		{Name: "zipf", Keys: 1},
		{Name: "zipf", Keys: 10, Skew: 0.9},
	}
	for _, s := range bad {
		if _, err := New(s); err == nil {
			t.Errorf("New(%+v) succeeded, want error", s)
		}
	}
}

func TestEveryWorkloadIsDeterministicAndInRange(t *testing.T) {
	for _, name := range Names() {
		t.Run(name, func(t *testing.T) {
			spec := Spec{Name: name, Keys: 1000, Seed: 7}
			g1, err := New(spec)
			if err != nil {
				t.Fatal(err)
			}
			g2, _ := New(spec)
			a, b := take(g1, 50_000), take(g2, 50_000)
			if !slices.Equal(a, b) {
				t.Fatal("same spec produced different streams")
			}
			for i, k := range a {
				if k < 0 || k >= spec.Keys {
					t.Fatalf("key %d at %d out of range", k, i)
				}
			}
		})
	}
}

func TestLoopCycles(t *testing.T) {
	g, _ := New(Spec{Name: "loop", Keys: 3})
	if got := take(g, 7); !slices.Equal(got, []int{0, 1, 2, 0, 1, 2, 0}) {
		t.Fatalf("loop = %v", got)
	}
}

// hitRatio replays the named workload against a fresh cache of each policy.
func hitRatios(t *testing.T, name string) (lru, lfu float64) {
	t.Helper()
	const keys, capacity, ops = 10_000, 500, 200_000
	run := func(c cache.Cache[int, int]) float64 {
		g, err := New(Spec{Name: name, Keys: keys, Seed: 1})
		if err != nil {
			t.Fatal(err)
		}
		return Replay(c, g, ops).HitRatio()
	}
	l, _ := cache.NewLRU[int, int](capacity)
	f, _ := cache.NewLFU[int, int](capacity)
	return run(l), run(f)
}

// The workloads exist to demonstrate trade-offs; these tests pin the
// direction of each one so a regression in either policy is noticed.
func TestPolicyTradeOffs(t *testing.T) {
	t.Run("scans pollute LRU but not LFU", func(t *testing.T) {
		if lru, lfu := hitRatios(t, "scan-mix"); lfu <= lru {
			t.Fatalf("scan-mix: LFU %.3f should beat LRU %.3f", lfu, lru)
		}
	})
	t.Run("shifting popularity strands LFU", func(t *testing.T) {
		if lru, lfu := hitRatios(t, "shift"); lru <= lfu {
			t.Fatalf("shift: LRU %.3f should beat LFU %.3f", lru, lfu)
		}
	})
	t.Run("a loop larger than the cache defeats both", func(t *testing.T) {
		if lru, lfu := hitRatios(t, "loop"); lru != 0 || lfu != 0 {
			t.Fatalf("loop: LRU %.3f LFU %.3f, want 0 for both", lru, lfu)
		}
	})
}
