// Command cachesim replays a synthetic workload against LRU and LFU caches
// and prints their hit ratios side by side, making the policies' trade-offs
// visible:
//
//	cachesim -workload scan-mix -capacity 500
package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"text/tabwriter"

	cache "github.com/abubakaromar18/software-engineering/projects/030-lru-lfu-caches"
	"github.com/abubakaromar18/software-engineering/projects/030-lru-lfu-caches/internal/workload"
)

// policies maps -policy names to constructors, in display order.
var policies = []struct {
	name string
	make func(capacity int) (cache.Cache[int, int], error)
}{
	{"LRU", func(c int) (cache.Cache[int, int], error) { return cache.NewLRU[int, int](c) }},
	{"LFU", func(c int) (cache.Cache[int, int], error) { return cache.NewLFU[int, int](c) }},
}

type options struct {
	spec     workload.Spec
	capacity int
	ops      int
	policy   string
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

// run is main without the process-global side effects, so it can be tested.
// It returns the exit code: 0 on success, 2 for usage errors, 1 otherwise.
func run(args []string, stdout, stderr io.Writer) int {
	opts, err := parseFlags(args, stderr)
	if errors.Is(err, flag.ErrHelp) {
		return 0
	}
	if err != nil {
		fmt.Fprintln(stderr, "cachesim:", err)
		return 2
	}
	if err := simulate(opts, stdout); err != nil {
		fmt.Fprintln(stderr, "cachesim:", err)
		return 1
	}
	return 0
}

func parseFlags(args []string, stderr io.Writer) (options, error) {
	var o options
	fs := flag.NewFlagSet("cachesim", flag.ContinueOnError)
	fs.SetOutput(stderr)
	fs.StringVar(&o.spec.Name, "workload", "zipf", "key stream: "+strings.Join(workload.Names(), ", "))
	fs.IntVar(&o.spec.Keys, "keys", 10_000, "number of distinct keys")
	fs.Uint64Var(&o.spec.Seed, "seed", 1, "PRNG seed (same seed, same result)")
	fs.Float64Var(&o.spec.Skew, "skew", 1.1, "Zipf exponent, > 1")
	fs.IntVar(&o.capacity, "capacity", 500, "cache capacity in entries")
	fs.IntVar(&o.ops, "ops", 200_000, "number of requests to replay")
	fs.StringVar(&o.policy, "policy", "all", "lru, lfu or all")
	if err := fs.Parse(args); err != nil {
		return o, err
	}
	if fs.NArg() > 0 {
		return o, fmt.Errorf("unexpected arguments: %v", fs.Args())
	}
	if o.ops < 1 {
		return o, fmt.Errorf("-ops must be positive (got %d)", o.ops)
	}
	switch o.policy = strings.ToLower(o.policy); o.policy {
	case "all", "lru", "lfu":
	default:
		return o, fmt.Errorf("-policy must be lru, lfu or all (got %q)", o.policy)
	}
	return o, nil
}

func simulate(o options, stdout io.Writer) error {
	fmt.Fprintf(stdout, "workload=%s keys=%d ops=%d capacity=%d seed=%d\n",
		o.spec.Name, o.spec.Keys, o.ops, o.capacity, o.spec.Seed)

	tw := tabwriter.NewWriter(stdout, 0, 0, 2, ' ', tabwriter.AlignRight)
	fmt.Fprintln(tw, "policy\thits\tmisses\tevictions\thit-ratio\t")
	for _, p := range policies {
		if o.policy != "all" && o.policy != strings.ToLower(p.name) {
			continue
		}
		c, err := p.make(o.capacity)
		if err != nil {
			return err
		}
		// A fresh generator per policy, so every policy sees the same stream.
		g, err := workload.New(o.spec)
		if err != nil {
			return err
		}
		s := workload.Replay(c, g, o.ops)
		fmt.Fprintf(tw, "%s\t%d\t%d\t%d\t%.2f%%\t\n", p.name, s.Hits, s.Misses, s.Evictions, 100*s.HitRatio())
	}
	return tw.Flush()
}
