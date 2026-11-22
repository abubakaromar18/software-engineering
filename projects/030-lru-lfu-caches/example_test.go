package cache_test

import (
	"fmt"

	cache "github.com/abubakaromar18/software-engineering/projects/030-lru-lfu-caches"
)

func ExampleNewLRU() {
	c, err := cache.NewLRU[string, int](2,
		cache.WithOnEvict(func(k string, v int) { fmt.Println("evicted", k) }))
	if err != nil {
		panic(err)
	}
	c.Put("a", 1)
	c.Put("b", 2)
	c.Get("a")    // a is now most recently used
	c.Put("c", 3) // so b goes
	fmt.Println(c.Keys())
	// Output:
	// evicted b
	// [c a]
}

func ExampleNewLFU() {
	c, _ := cache.NewLFU[string, int](2)
	c.Put("hot", 1)
	for range 3 {
		c.Get("hot")
	}
	c.Put("x", 2)
	c.Put("y", 3) // x and y both have frequency 1; x is older, so x goes
	freq, _ := c.Frequency("hot")
	fmt.Println(c.Keys(), freq)
	// Output: [hot y] 4
}

func ExampleNewShardedLRU() {
	c, _ := cache.NewShardedLRU[int, string](4, 1000)
	v, _ := c.GetOrLoad(42, func(k int) (string, error) {
		return fmt.Sprintf("user-%d", k), nil // e.g. a database read
	})
	fmt.Println(v, c.Len(), c.Cap())
	// Output: user-42 1 1000
}
