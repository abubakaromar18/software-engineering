package dev.omar.skiplist.bench;

import dev.omar.skiplist.GeometricLevelGenerator;
import dev.omar.skiplist.Range;
import dev.omar.skiplist.SkipListMap;
import dev.omar.skiplist.SkipListStats;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.NavigableMap;
import java.util.SplittableRandom;
import java.util.TreeMap;
import java.util.function.Supplier;

/**
 * A small, dependency-free micro-benchmark comparing {@link SkipListMap} with {@link TreeMap}.
 *
 * <p>Each workload runs a few warm-up rounds (so the JIT compiles the hot paths) and then
 * reports the best of several measured rounds in nanoseconds per operation. This is
 * deliberately simple — for publishable numbers use JMH, which also controls for dead-code
 * elimination, on-stack replacement and GC noise more rigorously.
 *
 * <p>Usage: {@code Benchmark [size] [seed]} (defaults: 200000, 42).
 */
public final class Benchmark {

    private static final int WARMUP_ROUNDS = 3;
    private static final int MEASURED_ROUNDS = 5;
    private static final int RANGE_WIDTH = 1_000;
    private static final int QUERIES = 20_000;

    /** The operations every benchmarked map must support; one adapter per implementation. */
    private interface Subject {
        String name();

        void put(int key, int value);

        int get(int key);

        /** Number of keys in {@code [lo, hi)}. */
        int countRange(int lo, int hi);

        /** Sum of values in {@code [lo, hi)}, forcing a real walk over the range. */
        long sumRange(int lo, int hi);
    }

    private record SkipListSubject(String name, SkipListMap<Integer, Integer> map) implements Subject {
        @Override public void put(int key, int value) { map.put(key, value); }
        @Override public int get(int key) { Integer v = map.get(key); return v == null ? 0 : v; }
        @Override public int countRange(int lo, int hi) { return map.range(Range.closedOpen(lo, hi)).size(); }
        @Override public long sumRange(int lo, int hi) {
            long sum = 0;
            for (Map.Entry<Integer, Integer> e : map.range(Range.closedOpen(lo, hi))) {
                sum += e.getValue();
            }
            return sum;
        }
    }

    private record TreeMapSubject(String name, NavigableMap<Integer, Integer> map) implements Subject {
        @Override public void put(int key, int value) { map.put(key, value); }
        @Override public int get(int key) { Integer v = map.get(key); return v == null ? 0 : v; }
        // TreeMap's subMap view has no order statistics: size() walks the whole range.
        @Override public int countRange(int lo, int hi) { return map.subMap(lo, true, hi, false).size(); }
        @Override public long sumRange(int lo, int hi) {
            long sum = 0;
            for (int v : map.subMap(lo, true, hi, false).values()) {
                sum += v;
            }
            return sum;
        }
    }

    private record Result(String subject, String workload, double nanosPerOp) {}

    /** Prevents the JIT from discarding results as dead code. */
    private static long sink;

    private Benchmark() {}

    public static void main(String[] args) {
        int size = args.length > 0 ? parsePositive(args[0], "size") : 200_000;
        long seed = args.length > 1 ? Long.parseLong(args[1]) : 42L;

        int[] keys = new SplittableRandom(seed).ints(size, 0, size * 4).toArray();
        int[] probes = new SplittableRandom(seed + 1).ints(QUERIES, 0, size * 4).toArray();

        List<Supplier<Subject>> factories = List.of(
                () -> new SkipListSubject("SkipListMap p=1/2",
                        new SkipListMap<>(null, new GeometricLevelGenerator(0.5, new SplittableRandom(seed)))),
                () -> new SkipListSubject("SkipListMap p=1/4",
                        new SkipListMap<>(null, new GeometricLevelGenerator(0.25, new SplittableRandom(seed)))),
                () -> new TreeMapSubject("TreeMap", new TreeMap<>()));

        System.out.printf(Locale.ROOT, "%d random inserts, %d queries, range width %d, seed %d%n%n",
                size, QUERIES, RANGE_WIDTH, seed);

        List<Result> results = new ArrayList<>();
        for (Supplier<Subject> factory : factories) {
            results.addAll(run(factory, keys, probes));
        }
        printTable(results);

        System.out.println();
        for (double p : new double[] {0.5, 0.25}) {
            SkipListMap<Integer, Integer> map =
                    new SkipListMap<>(null, new GeometricLevelGenerator(p, new SplittableRandom(seed)));
            for (int k : keys) {
                map.put(k, k);
            }
            SkipListStats stats = map.stats();
            System.out.printf(Locale.ROOT, "p=%.2f: %d entries, %d levels, %.2f pointers/entry, first levels %s%n",
                    p, stats.size(), stats.levels(), stats.pointersPerEntry(),
                    stats.nodesPerLevel().subList(0, Math.min(6, stats.levels())));
        }
    }

    private static List<Result> run(Supplier<Subject> factory, int[] keys, int[] probes) {
        double insert = Double.MAX_VALUE;
        double get = Double.MAX_VALUE;
        double count = Double.MAX_VALUE;
        double sum = Double.MAX_VALUE;
        String name = null;

        for (int round = 0; round < WARMUP_ROUNDS + MEASURED_ROUNDS; round++) {
            boolean measured = round >= WARMUP_ROUNDS;
            Subject subject = factory.get();
            name = subject.name();

            long t0 = System.nanoTime();
            for (int i = 0; i < keys.length; i++) {
                subject.put(keys[i], i);
            }
            long t1 = System.nanoTime();
            long acc = 0;
            for (int p : probes) {
                acc += subject.get(p);
            }
            long t2 = System.nanoTime();
            for (int p : probes) {
                acc += subject.countRange(p, p + RANGE_WIDTH);
            }
            long t3 = System.nanoTime();
            for (int p : probes) {
                acc += subject.sumRange(p, p + RANGE_WIDTH);
            }
            long t4 = System.nanoTime();
            sink += acc;

            if (measured) {
                insert = Math.min(insert, (double) (t1 - t0) / keys.length);
                get = Math.min(get, (double) (t2 - t1) / probes.length);
                count = Math.min(count, (double) (t3 - t2) / probes.length);
                sum = Math.min(sum, (double) (t4 - t3) / probes.length);
            }
        }
        return List.of(
                new Result(name, "put", insert),
                new Result(name, "get", get),
                new Result(name, "range count", count),
                new Result(name, "range iterate", sum));
    }

    private static void printTable(List<Result> results) {
        List<String> subjects = results.stream().map(Result::subject).distinct().toList();
        List<String> workloads = results.stream().map(Result::workload).distinct().toList();

        System.out.printf(Locale.ROOT, "%-15s", "ns/op");
        subjects.forEach(s -> System.out.printf(Locale.ROOT, "%20s", s));
        System.out.println();
        for (String w : workloads) {
            System.out.printf(Locale.ROOT, "%-15s", w);
            for (String s : subjects) {
                double ns = results.stream()
                        .filter(r -> r.subject().equals(s) && r.workload().equals(w))
                        .findFirst().orElseThrow().nanosPerOp();
                System.out.printf(Locale.ROOT, "%20.1f", ns);
            }
            System.out.println();
        }
        if (sink == 42) {
            System.out.println(); // unreachable in practice; keeps `sink` observable
        }
    }

    private static int parsePositive(String text, String what) {
        try {
            int value = Integer.parseInt(text);
            if (value <= 0) {
                throw new IllegalArgumentException(what + " must be positive: " + text);
            }
            return value;
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(what + " must be an integer: " + text, e);
        }
    }
}
