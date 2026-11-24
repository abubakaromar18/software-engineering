package dev.omar.skiplist;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.AbstractMap.SimpleImmutableEntry;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.PrimitiveIterator;
import java.util.SplittableRandom;
import java.util.TreeMap;
import java.util.stream.IntStream;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SkipListMapTest {

    private SkipListMap<Integer, String> map;

    @BeforeEach
    void setUp() {
        map = new SkipListMap<>(null, new GeometricLevelGenerator(7));
    }

    private void putAll(int... keys) {
        for (int k : keys) {
            map.put(k, "v" + k);
        }
    }

    @Nested
    @DisplayName("basic map operations")
    class Basics {

        @Test
        void emptyMap() {
            assertAll(
                    () -> assertEquals(0, map.size()),
                    () -> assertTrue(map.isEmpty()),
                    () -> assertNull(map.get(1)),
                    () -> assertFalse(map.containsKey(1)),
                    () -> assertNull(map.remove(1)),
                    () -> assertNull(map.firstEntry()),
                    () -> assertNull(map.lastEntry()),
                    () -> assertNull(map.pollFirstEntry()));
            map.checkInvariants();
        }

        @Test
        void putGetAndReplace() {
            assertNull(map.put(5, "five"));
            assertNull(map.put(1, "one"));
            assertEquals("five", map.put(5, "FIVE"));
            assertEquals(2, map.size());
            assertEquals("FIVE", map.get(5));
            assertEquals("one", map.get(1));
            map.checkInvariants();
        }

        @Test
        void nullValuesAreAllowedAndDistinguishableViaContainsKey() {
            map.put(3, null);
            assertTrue(map.containsKey(3));
            assertNull(map.get(3));
            assertFalse(map.containsKey(4));
        }

        @Test
        void nullKeysAreRejected() {
            assertAll(
                    () -> assertThrows(NullPointerException.class, () -> map.put(null, "x")),
                    () -> assertThrows(NullPointerException.class, () -> map.get(null)),
                    () -> assertThrows(NullPointerException.class, () -> map.remove(null)),
                    () -> assertThrows(NullPointerException.class, () -> map.floorKey(null)),
                    () -> assertThrows(NullPointerException.class, () -> map.rank(null)));
        }

        @Test
        void removeReturnsOldValueAndShrinks() {
            putAll(4, 2, 8, 6);
            assertEquals("v2", map.remove(2));
            assertNull(map.remove(2));
            assertEquals(List.of(4, 6, 8), new ArrayList<>(map.keySet()));
            map.checkInvariants();
        }

        @Test
        void clearResetsEverything() {
            putAll(IntStream.range(0, 500).toArray());
            map.clear();
            assertTrue(map.isEmpty());
            map.checkInvariants();
            map.put(1, "again");
            assertEquals("again", map.get(1));
            map.checkInvariants();
        }

        @Test
        void equalsAndHashCodeFollowTheMapContract() {
            putAll(3, 1, 2);
            TreeMap<Integer, String> expected = new TreeMap<>(Map.of(1, "v1", 2, "v2", 3, "v3"));
            assertEquals(expected, map);
            assertEquals(map, expected);
            assertEquals(expected.hashCode(), map.hashCode());
            assertEquals("{1=v1, 2=v2, 3=v3}", map.toString());
        }

        @Test
        void wrongKeyTypeFailsWithClassCastException() {
            putAll(1);
            assertThrows(ClassCastException.class, () -> map.get("not an integer"));
        }
    }

    @Nested
    @DisplayName("ordering and navigation")
    class Navigation {

        @BeforeEach
        void fill() {
            putAll(50, 10, 40, 20, 30);
        }

        @Test
        void iteratesInAscendingOrder() {
            assertEquals(List.of(10, 20, 30, 40, 50), new ArrayList<>(map.keySet()));
        }

        @Test
        void firstAndLast() {
            assertEquals(10, map.firstKey());
            assertEquals(50, map.lastKey());
            assertEquals(new SimpleImmutableEntry<>(50, "v50"), map.lastEntry());
        }

        @Test
        void firstKeyOnEmptyMapThrows() {
            map.clear();
            assertThrows(NoSuchElementException.class, () -> map.firstKey());
            assertThrows(NoSuchElementException.class, () -> map.lastKey());
        }

        @Test
        void floorCeilingLowerHigher() {
            assertAll(
                    () -> assertEquals(30, map.floorKey(30)),
                    () -> assertEquals(30, map.floorKey(35)),
                    () -> assertNull(map.floorKey(5)),
                    () -> assertEquals(20, map.lowerKey(30)),
                    () -> assertNull(map.lowerKey(10)),
                    () -> assertEquals(30, map.ceilingKey(30)),
                    () -> assertEquals(40, map.ceilingKey(31)),
                    () -> assertNull(map.ceilingKey(51)),
                    () -> assertEquals(40, map.higherKey(30)),
                    () -> assertNull(map.higherKey(50)));
        }

        @Test
        void navigationReturnsImmutableSnapshots() {
            Map.Entry<Integer, String> e = map.floorEntry(30);
            assertThrows(UnsupportedOperationException.class, () -> e.setValue("x"));
        }

        @Test
        void pollFirstRemovesInOrder() {
            assertEquals(10, map.pollFirstEntry().getKey());
            assertEquals(20, map.pollFirstEntry().getKey());
            assertEquals(3, map.size());
            map.checkInvariants();
        }

        @Test
        void customComparatorReversesOrder() {
            SkipListMap<String, Integer> byLengthDesc = new SkipListMap<>(
                    Comparator.comparingInt(String::length).reversed().thenComparing(Comparator.naturalOrder()),
                    new GeometricLevelGenerator(1));
            for (String s : List.of("a", "ccc", "bb", "dddd", "ab")) {
                byLengthDesc.put(s, s.length());
            }
            assertEquals(List.of("dddd", "ccc", "ab", "bb", "a"), new ArrayList<>(byLengthDesc.keySet()));
            assertEquals("a", byLengthDesc.ceilingKey("zz")); // "zz" sorts after "bb", before "a"
            assertNull(byLengthDesc.ceilingKey("b"));
        }
    }

    @Nested
    @DisplayName("rank and select")
    class OrderStatistics {

        @Test
        void rankCountsStrictlySmallerKeys() {
            putAll(10, 20, 30);
            assertAll(
                    () -> assertEquals(0, map.rank(5)),
                    () -> assertEquals(0, map.rank(10)),
                    () -> assertEquals(1, map.rank(15)),
                    () -> assertEquals(2, map.rank(30)),
                    () -> assertEquals(3, map.rank(99)));
        }

        @Test
        void selectIsTheInverseOfRank() {
            int[] keys = new SplittableRandom(3).ints(2_000, 0, 1_000_000).distinct().toArray();
            putAll(keys);
            for (int i = 0; i < map.size(); i++) {
                Integer key = map.select(i).getKey();
                assertEquals(i, map.rank(key), "rank(select(" + i + "))");
            }
        }

        @Test
        void selectOutOfBoundsThrows() {
            putAll(1, 2);
            assertThrows(IndexOutOfBoundsException.class, () -> map.select(-1));
            assertThrows(IndexOutOfBoundsException.class, () -> map.select(2));
        }

        @Test
        void selectFindsMedian() {
            putAll(IntStream.rangeClosed(1, 101).map(i -> i * 3).toArray());
            assertEquals(153, map.select(50).getKey());
        }
    }

    @Nested
    @DisplayName("iterators")
    class Iterators {

        @Test
        void iteratorRemoveDeletesCurrentEntry() {
            putAll(IntStream.range(0, 100).toArray());
            Iterator<Map.Entry<Integer, String>> it = map.entrySet().iterator();
            while (it.hasNext()) {
                if (it.next().getKey() % 2 == 0) {
                    it.remove();
                }
            }
            assertEquals(50, map.size());
            assertTrue(map.keySet().stream().allMatch(k -> k % 2 == 1));
            map.checkInvariants();
        }

        @Test
        void removeTwiceOrBeforeNextIsIllegal() {
            putAll(1, 2);
            Iterator<Integer> it = map.keySet().iterator();
            assertThrows(IllegalStateException.class, it::remove);
            it.next();
            it.remove();
            assertThrows(IllegalStateException.class, it::remove);
        }

        @Test
        void structuralModificationDuringIterationFailsFast() {
            putAll(1, 2, 3);
            Iterator<Integer> it = map.keySet().iterator();
            it.next();
            map.put(4, "v4");
            assertThrows(ConcurrentModificationException.class, it::next);
        }

        @Test
        void replacingAValueIsNotAStructuralModification() {
            putAll(1, 2, 3);
            Iterator<Integer> it = map.keySet().iterator();
            it.next();
            map.put(2, "updated");
            assertEquals(2, it.next());
        }

        @Test
        void setValueWritesThrough() {
            putAll(1, 2);
            for (Map.Entry<Integer, String> e : map.entrySet()) {
                e.setValue(e.getValue().toUpperCase());
            }
            assertEquals("V2", map.get(2));
        }

        @Test
        void exhaustedIteratorThrows() {
            Iterator<Integer> it = map.keySet().iterator();
            assertFalse(it.hasNext());
            assertThrows(NoSuchElementException.class, it::next);
        }
    }

    @Nested
    @DisplayName("structure")
    class Structure {

        @Test
        void scriptedLevelsProduceTheExpectedShape() {
            // Heights for keys 1..6 in insertion order; a hand-checkable tower layout:
            // level 2:  .  .  3  .  .  .
            // level 1:  .  2  3  .  5  .
            // level 0:  1  2  3  4  5  6
            PrimitiveIterator.OfInt heights = IntStream.of(1, 2, 3, 1, 2, 1).iterator();
            SkipListMap<Integer, String> shaped = new SkipListMap<>(null, max -> heights.nextInt());
            for (int k = 1; k <= 6; k++) {
                shaped.put(k, "v" + k);
            }
            SkipListStats stats = shaped.stats();
            assertEquals(3, stats.levels());
            assertEquals(List.of(6, 3, 1), stats.nodesPerLevel());
            assertEquals(10, stats.forwardPointers());
            shaped.checkInvariants();

            assertEquals(2, shaped.rank(3));
            assertEquals(5, shaped.select(4).getKey());

            shaped.remove(3); // removing the only top-level node drops a level
            assertEquals(2, shaped.stats().levels());
            shaped.checkInvariants();
        }

        @Test
        void misbehavingLevelGeneratorIsReported() {
            SkipListMap<Integer, String> broken = new SkipListMap<>(null, max -> max + 1);
            assertThrows(IllegalStateException.class, () -> broken.put(1, "x"));
            assertTrue(broken.isEmpty());
        }

        @Test
        void levelsGrowLogarithmically() {
            putAll(IntStream.range(0, 65_536).toArray());
            SkipListStats stats = map.stats();
            // log2(65536) = 16; with p = 1/2 the height concentrates tightly around it.
            assertTrue(stats.levels() >= 12 && stats.levels() <= 24, "levels = " + stats.levels());
            assertEquals(2.0, stats.pointersPerEntry(), 0.1);
        }
    }
}
