package cache

import (
	"math/rand/v2"
	"strconv"
	"testing"
)

// Benchmarks use a Zipf key distribution, which is closer to real traffic
// than uniform keys and keeps the hit ratio in a realistic range.

const benchKeys = 1 << 16

func zipfKeys(n int) []int {
	r := rand.New(rand.NewPCG(1, 2))
	z := rand.NewZipf(r, 1.1, 1, benchKeys-1)
	keys := make([]int, n)
	for i := range keys {
		keys[i] = int(z.Uint64())
	}
	return keys
}

func benchmarkPolicy(b *testing.B, c Cache[int, int]) {
	keys := zipfKeys(1 << 14)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		k := keys[i&(len(keys)-1)]
		if _, ok := c.Get(k); !ok {
			c.Put(k, k)
		}
	}
	b.ReportMetric(100*c.Stats().HitRatio(), "hit%")
}

func BenchmarkGetOrPut(b *testing.B) {
	for _, capacity := range []int{1 << 8, 1 << 12} {
		b.Run("LRU/cap="+strconv.Itoa(capacity), func(b *testing.B) {
			c, _ := NewLRU[int, int](capacity)
			benchmarkPolicy(b, c)
		})
		b.Run("LFU/cap="+strconv.Itoa(capacity), func(b *testing.B) {
			c, _ := NewLFU[int, int](capacity)
			benchmarkPolicy(b, c)
		})
	}
}

// BenchmarkParallel compares one lock against sharded locks under contention.
// Run with -cpu=1,4,8 to see sharding pay off as parallelism grows.
func BenchmarkParallel(b *testing.B) {
	const capacity = 1 << 12
	makers := map[string]func() Cache[int, int]{
		"Synchronized": func() Cache[int, int] {
			c, _ := NewLRU[int, int](capacity)
			return NewSynchronized[int, int](c)
		},
		"Sharded16": func() Cache[int, int] {
			c, _ := NewShardedLRU[int, int](16, capacity)
			return c
		},
	}
	keys := zipfKeys(1 << 14)
	for name, mk := range makers {
		b.Run(name, func(b *testing.B) {
			c := mk()
			b.RunParallel(func(pb *testing.PB) {
				i := rand.IntN(len(keys))
				for pb.Next() {
					k := keys[i&(len(keys)-1)]
					i++
					if _, ok := c.Get(k); !ok {
						c.Put(k, k)
					}
				}
			})
		})
	}
}
