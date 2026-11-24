package dev.omar.skiplist;

import java.util.Objects;
import java.util.SplittableRandom;
import java.util.random.RandomGenerator;

/**
 * The classic Pugh level generator: a node of height {@code h} is promoted to {@code h + 1}
 * with probability {@code p}, so heights follow a geometric distribution with
 * {@code P(height >= k) = p^(k-1)}.
 *
 * <p>Trade-off of {@code p}: Pugh shows the expected search cost is about
 * {@code (1/p) log_{1/p} n}, which is the same {@code 2 log2 n} for {@code p = 1/2} and
 * {@code p = 1/4}. The smaller {@code p} needs fewer pointers per node ({@code 1/(1-p)}: 1.33 vs
 * 2) but has higher variance in search time. Redis uses 1/4; we default to 1/2 for steadier
 * latency, and the benchmark lets you compare both.
 */
public final class GeometricLevelGenerator implements LevelGenerator {

    /** Promotion probability used by {@link #GeometricLevelGenerator()}. */
    public static final double DEFAULT_PROBABILITY = 0.5;

    private final double probability;
    private final RandomGenerator random;

    /** A generator with {@code p = 1/2} seeded from a fresh {@link SplittableRandom}. */
    public GeometricLevelGenerator() {
        this(DEFAULT_PROBABILITY, new SplittableRandom());
    }

    /** A reproducible generator with {@code p = 1/2}, handy for tests and benchmarks. */
    public GeometricLevelGenerator(long seed) {
        this(DEFAULT_PROBABILITY, new SplittableRandom(seed));
    }

    /**
     * @param probability promotion probability, strictly between 0 and 1
     * @param random      source of randomness; never shared across threads by this class
     */
    public GeometricLevelGenerator(double probability, RandomGenerator random) {
        if (!(probability > 0.0 && probability < 1.0)) {
            throw new IllegalArgumentException("probability must be in (0, 1): " + probability);
        }
        this.probability = probability;
        this.random = Objects.requireNonNull(random, "random");
    }

    public double probability() {
        return probability;
    }

    @Override
    public int nextLevel(int maxLevel) {
        if (maxLevel < 1) {
            throw new IllegalArgumentException("maxLevel must be >= 1: " + maxLevel);
        }
        int level = 1;
        while (level < maxLevel && random.nextDouble() < probability) {
            level++;
        }
        return level;
    }
}
