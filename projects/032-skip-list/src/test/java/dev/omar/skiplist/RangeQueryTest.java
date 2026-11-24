package dev.omar.skiplist;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RangeQueryTest {

    private SkipListMap<Integer, String> map;

    @BeforeEach
    void setUp() {
        map = new SkipListMap<>(null, new GeometricLevelGenerator(11));
        for (int k = 10; k <= 100; k += 10) {
            map.put(k, "v" + k);
        }
    }

    static Stream<Arguments> ranges() {
        return Stream.of(
                Arguments.of(Range.closed(20, 50), List.of(20, 30, 40, 50)),
                Arguments.of(Range.open(20, 50), List.of(30, 40)),
                Arguments.of(Range.closedOpen(20, 50), List.of(20, 30, 40)),
                Arguments.of(Range.closed(25, 55), List.of(30, 40, 50)),
                Arguments.of(Range.atLeast(90), List.of(90, 100)),
                Arguments.of(Range.greaterThan(90), List.of(100)),
                Arguments.of(Range.atMost(20), List.of(10, 20)),
                Arguments.of(Range.lessThan(20), List.of(10)),
                Arguments.of(Range.closed(30, 30), List.of(30)),
                Arguments.of(Range.open(30, 30), List.of()),
                Arguments.of(Range.open(30, 40), List.of()),
                Arguments.of(Range.closed(101, 200), List.of()),
                Arguments.of(Range.closed(-5, 5), List.of()),
                Arguments.of(Range.all(), List.of(10, 20, 30, 40, 50, 60, 70, 80, 90, 100)));
    }

    @ParameterizedTest(name = "{0} -> {1}")
    @MethodSource("ranges")
    void iteratesExactlyTheKeysInRange(Range<Integer> range, List<Integer> expected) {
        assertEquals(expected, map.range(range).keys());
    }

    @ParameterizedTest(name = "size of {0} is {1}.size()")
    @MethodSource("ranges")
    void sizeMatchesIterationWithoutWalking(Range<Integer> range, List<Integer> expected) {
        SkipListMap<Integer, String>.RangeView view = map.range(range);
        assertEquals(expected.size(), view.size());
        assertEquals(expected.isEmpty(), view.isEmpty());
    }

    @Test
    void streamSupportsStandardOperations() {
        int sum = map.range(Range.closed(20, 40)).stream().mapToInt(Map.Entry::getKey).sum();
        assertEquals(90, sum);
    }

    @Test
    void invertedRangeIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> map.range(Range.closed(50, 20)));
    }

    @Test
    void nullBoundsMustUseUnboundedFactories() {
        assertThrows(NullPointerException.class, () -> Range.closed(null, 5));
        assertThrows(NullPointerException.class, () -> Range.atLeast(null));
    }

    @Test
    void viewIsLive() {
        SkipListMap<Integer, String>.RangeView view = map.range(Range.closed(20, 40));
        map.put(35, "v35");
        map.remove(20);
        assertEquals(List.of(30, 35, 40), view.keys());
        assertEquals(3, view.size());
    }

    @Test
    void rangeIteratorIsFailFastAndSupportsRemove() {
        Iterator<Map.Entry<Integer, String>> it = map.range(Range.closed(20, 60)).iterator();
        it.next();
        it.remove(); // removes 20 through the view
        assertEquals(List.of(30, 40, 50, 60), map.range(Range.closed(20, 60)).keys());
        map.put(55, "v55");
        assertThrows(ConcurrentModificationException.class, it::next);
        map.checkInvariants();
    }

    @Test
    void rangeToStringIsReadable() {
        assertEquals("[1, 5)", Range.closedOpen(1, 5).toString());
        assertEquals("(-inf, 3]", Range.atMost(3).toString());
        assertEquals("(-inf, +inf)", Range.all().toString());
        assertTrue(Range.greaterThan(2).hasLower());
    }
}
