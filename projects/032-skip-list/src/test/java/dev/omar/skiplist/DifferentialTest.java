package dev.omar.skiplist;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.Map;
import java.util.NavigableMap;
import java.util.SplittableRandom;
import java.util.TreeMap;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Model-based (differential) testing: drive a {@link SkipListMap} and a {@link TreeMap} with the
 * same long random sequence of operations and require identical observable behaviour after
 * every step. TreeMap is the trusted oracle; any divergence points at a bug in the skip list.
 * The structural invariants (ordering, spans, level count) are re-verified periodically.
 */
class DifferentialTest {

    private static final int OPERATIONS = 20_000;
    private static final int KEY_SPACE = 2_000; // small enough to produce many hits and replaces

    @ParameterizedTest(name = "seed {0}, p = 1/2")
    @ValueSource(longs = {1, 2, 3, 42, 2026})
    void agreesWithTreeMapAtHalf(long seed) {
        runAgainstOracle(seed, 0.5);
    }

    @ParameterizedTest(name = "seed {0}, p = 1/4")
    @ValueSource(longs = {7, 99})
    void agreesWithTreeMapAtQuarter(long seed) {
        runAgainstOracle(seed, 0.25);
    }

    private void runAgainstOracle(long seed, double p) {
        SplittableRandom random = new SplittableRandom(seed);
        SkipListMap<Integer, Integer> actual =
                new SkipListMap<>(null, new GeometricLevelGenerator(p, new SplittableRandom(seed * 31)));
        NavigableMap<Integer, Integer> expected = new TreeMap<>();

        for (int step = 0; step < OPERATIONS; step++) {
            int key = random.nextInt(KEY_SPACE);
            int value = random.nextInt();
            String where = "seed " + seed + ", step " + step + ", key " + key;

            switch (random.nextInt(10)) {
                case 0, 1, 2, 3 -> assertEquals(expected.put(key, value), actual.put(key, value), where);
                case 4, 5 -> assertEquals(expected.remove(key), actual.remove(key), where);
                case 6 -> {
                    assertEquals(expected.get(key), actual.get(key), where);
                    assertEquals(expected.floorKey(key), actual.floorKey(key), where);
                    assertEquals(expected.ceilingKey(key), actual.ceilingKey(key), where);
                    assertEquals(expected.lowerKey(key), actual.lowerKey(key), where);
                    assertEquals(expected.higherKey(key), actual.higherKey(key), where);
                }
                case 7 -> {
                    int hi = key + random.nextInt(200);
                    boolean loInc = random.nextBoolean();
                    boolean hiInc = random.nextBoolean();
                    NavigableMap<Integer, Integer> sub = expected.subMap(key, loInc, hi, hiInc);
                    SkipListMap<Integer, Integer>.RangeView view =
                            actual.range(new Range<>(key, loInc, hi, hiInc));
                    assertEquals(sub.size(), view.size(), where);
                    assertEquals(new ArrayList<>(sub.keySet()), view.keys(), where);
                }
                case 8 -> {
                    assertEquals(expected.headMap(key, false).size(), actual.rank(key), where);
                    if (!expected.isEmpty()) {
                        int index = random.nextInt(expected.size());
                        assertEquals(nth(expected, index), actual.select(index).getKey(), where);
                    }
                }
                default -> removeEveryThirdViaIterator(expected, actual, key, where);
            }
            assertEquals(expected.size(), actual.size(), where);
            if (step % 1_000 == 0) {
                actual.checkInvariants();
            }
        }
        actual.checkInvariants();
        assertEquals(expected, actual);
        assertEquals(new ArrayList<>(expected.entrySet()), new ArrayList<>(actual.entrySet()));
    }

    /** Exercises Iterator.remove on both maps over the same small window. */
    private static void removeEveryThirdViaIterator(NavigableMap<Integer, Integer> expected,
                                                    SkipListMap<Integer, Integer> actual,
                                                    int from, String where) {
        Iterator<Map.Entry<Integer, Integer>> e = expected.subMap(from, true, from + 30, false).entrySet().iterator();
        Iterator<Map.Entry<Integer, Integer>> a = actual.range(Range.closedOpen(from, from + 30)).iterator();
        int i = 0;
        while (e.hasNext()) {
            assertEquals(e.next(), a.next(), where);
            if (i++ % 3 == 0) {
                e.remove();
                a.remove();
            }
        }
        assertEquals(false, a.hasNext(), where);
    }

    private static Integer nth(NavigableMap<Integer, Integer> map, int index) {
        Iterator<Integer> it = map.keySet().iterator();
        for (int i = 0; i < index; i++) {
            it.next();
        }
        return it.next();
    }
}
