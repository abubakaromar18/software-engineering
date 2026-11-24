package dev.omar.skiplist;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.SplittableRandom;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class GeometricLevelGeneratorTest {

    private static final int SAMPLES = 200_000;

    @ParameterizedTest(name = "p = {0}")
    @ValueSource(doubles = {0.5, 0.25})
    void heightsFollowAGeometricDistribution(double p) {
        GeometricLevelGenerator generator = new GeometricLevelGenerator(p, new SplittableRandom(5));
        int[] atLeast = new int[SkipListMap.MAX_LEVEL + 2];
        long total = 0;
        for (int i = 0; i < SAMPLES; i++) {
            int h = generator.nextLevel(SkipListMap.MAX_LEVEL);
            total += h;
            for (int k = 1; k <= h; k++) {
                atLeast[k]++;
            }
        }
        // P(height >= k) = p^(k-1); check the first few levels within 2% absolute.
        for (int k = 1; k <= 4; k++) {
            double observed = (double) atLeast[k] / SAMPLES;
            assertEquals(Math.pow(p, k - 1), observed, 0.02, "P(h >= " + k + ")");
        }
        // Mean height (= pointers per node) is 1 / (1 - p).
        assertEquals(1 / (1 - p), (double) total / SAMPLES, 0.02);
    }

    @Test
    void neverExceedsMaxLevel() {
        GeometricLevelGenerator generator = new GeometricLevelGenerator(0.99, new SplittableRandom(1));
        for (int i = 0; i < 1_000; i++) {
            int h = generator.nextLevel(3);
            assertTrue(h >= 1 && h <= 3, "h = " + h);
        }
    }

    @Test
    void sameSeedSameSequence() {
        GeometricLevelGenerator a = new GeometricLevelGenerator(123);
        GeometricLevelGenerator b = new GeometricLevelGenerator(123);
        for (int i = 0; i < 1_000; i++) {
            assertEquals(a.nextLevel(32), b.nextLevel(32));
        }
    }

    @ParameterizedTest
    @ValueSource(doubles = {0.0, 1.0, -0.1, 1.5, Double.NaN})
    void rejectsInvalidProbabilities(double p) {
        assertThrows(IllegalArgumentException.class, () -> new GeometricLevelGenerator(p, new SplittableRandom()));
    }

    @Test
    void rejectsNonPositiveMaxLevel() {
        assertThrows(IllegalArgumentException.class, () -> new GeometricLevelGenerator(1).nextLevel(0));
    }
}
