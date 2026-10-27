package dev.omar.money;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Arrays;
import java.util.SplittableRandom;
import java.util.stream.LongStream;
import java.util.stream.Stream;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

/**
 * Property-style tests: invariants checked against many generated inputs rather than a few
 * hand-picked examples. A fixed seed keeps failures reproducible; each case prints its inputs
 * in the test name so a failure can be turned into a regular example test.
 */
class AllocationPropertiesTest {

    private static final long SEED = 20261027L;
    private static final int CASES = 500;

    static Stream<Arguments> allocations() {
        SplittableRandom random = new SplittableRandom(SEED);
        return Stream.generate(() -> {
            long minor = random.nextLong(-1_000_000_000_000L, 1_000_000_000_000L);
            long[] ratios = LongStream.generate(() -> random.nextInt(4) == 0 ? 0 : random.nextLong(1, 1_000))
                    .limit(random.nextInt(1, 20))
                    .toArray();
            ratios[random.nextInt(ratios.length)] = random.nextLong(1, 1_000); // at least one positive
            return Arguments.of(minor, ratios);
        }).limit(CASES);
    }

    @ParameterizedTest(name = "{0} by {1}")
    @MethodSource("allocations")
    void partsSumToOriginalAndStayWithinOneUnitOfExactShare(long minor, long[] ratios) {
        long[] parts = Money.ofMinor(minor, Currency.USD).allocate(ratios).stream()
                .mapToLong(Money::minorUnits)
                .toArray();
        long ratioSum = Arrays.stream(ratios).sum();

        assertEquals(ratios.length, parts.length);
        assertEquals(minor, Arrays.stream(parts).sum(), "no cent may be created or lost");
        for (int i = 0; i < ratios.length; i++) {
            BigDecimal exact = BigDecimal.valueOf(minor).multiply(BigDecimal.valueOf(ratios[i]))
                    .divide(BigDecimal.valueOf(ratioSum), 10, RoundingMode.HALF_EVEN);
            BigDecimal drift = BigDecimal.valueOf(parts[i]).subtract(exact).abs();
            assertTrue(drift.compareTo(BigDecimal.ONE) < 0, "part " + i + " drifted by " + drift);
            if (ratios[i] == 0) {
                assertEquals(0, parts[i], "a zero ratio must receive nothing");
            }
        }
    }

    static Stream<Arguments> splits() {
        SplittableRandom random = new SplittableRandom(SEED + 1);
        return Stream.generate(() -> Arguments.of(
                random.nextLong(-1_000_000_000L, 1_000_000_000L), random.nextInt(1, 50))).limit(CASES);
    }

    @ParameterizedTest(name = "{0} into {1}")
    @MethodSource("splits")
    void equalSplitPartsDifferByAtMostOneAndLargerPartsComeFirst(long minor, int n) {
        long[] parts = Money.ofMinor(minor, Currency.EUR).split(n).stream()
                .mapToLong(m -> m.abs().minorUnits())
                .toArray();

        long max = Arrays.stream(parts).max().orElseThrow();
        long min = Arrays.stream(parts).min().orElseThrow();
        assertTrue(max - min <= 1);
        for (int i = 1; i < parts.length; i++) {
            assertTrue(parts[i - 1] >= parts[i], "extra units must go to the earliest parts");
        }
    }

    static Stream<Arguments> pairs() {
        SplittableRandom random = new SplittableRandom(SEED + 2);
        return Stream.generate(() -> Arguments.of(
                random.nextLong(-1_000_000_000_000L, 1_000_000_000_000L),
                random.nextLong(-1_000_000_000_000L, 1_000_000_000_000L))).limit(CASES);
    }

    @ParameterizedTest(name = "{0}, {1}")
    @MethodSource("pairs")
    void additionIsCommutativeAndUndoneBySubtraction(long a, long b) {
        Money x = Money.ofMinor(a, Currency.USD);
        Money y = Money.ofMinor(b, Currency.USD);
        assertEquals(x.plus(y), y.plus(x));
        assertEquals(x, x.plus(y).minus(y));
        assertEquals(Integer.signum(Long.compare(a, b)), Integer.signum(x.compareTo(y)));
    }
}
