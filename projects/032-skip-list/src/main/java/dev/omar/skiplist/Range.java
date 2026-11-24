package dev.omar.skiplist;

/**
 * An interval of keys with independently open, closed or absent ends.
 *
 * <p>A {@code null} bound means "unbounded on that side". The range does not know how keys are
 * ordered, so checking that {@code lower <= upper} is left to the map that owns the comparator
 * (see {@link SkipListMap#range(Range)}).
 *
 * @param lower          lowest key, or {@code null} for no lower bound
 * @param lowerInclusive whether {@code lower} itself is included (ignored when unbounded)
 * @param upper          highest key, or {@code null} for no upper bound
 * @param upperInclusive whether {@code upper} itself is included (ignored when unbounded)
 */
public record Range<K>(K lower, boolean lowerInclusive, K upper, boolean upperInclusive) {

    /** {@code [lower, upper]} */
    public static <K> Range<K> closed(K lower, K upper) {
        return new Range<>(requireBound(lower), true, requireBound(upper), true);
    }

    /** {@code (lower, upper)} */
    public static <K> Range<K> open(K lower, K upper) {
        return new Range<>(requireBound(lower), false, requireBound(upper), false);
    }

    /** {@code [lower, upper)} — the half-open form most loops want. */
    public static <K> Range<K> closedOpen(K lower, K upper) {
        return new Range<>(requireBound(lower), true, requireBound(upper), false);
    }

    /** {@code [lower, +inf)} */
    public static <K> Range<K> atLeast(K lower) {
        return new Range<>(requireBound(lower), true, null, false);
    }

    /** {@code (lower, +inf)} */
    public static <K> Range<K> greaterThan(K lower) {
        return new Range<>(requireBound(lower), false, null, false);
    }

    /** {@code (-inf, upper]} */
    public static <K> Range<K> atMost(K upper) {
        return new Range<>(null, false, requireBound(upper), true);
    }

    /** {@code (-inf, upper)} */
    public static <K> Range<K> lessThan(K upper) {
        return new Range<>(null, false, requireBound(upper), false);
    }

    /** Every key. */
    public static <K> Range<K> all() {
        return new Range<>(null, false, null, false);
    }

    public boolean hasLower() {
        return lower != null;
    }

    public boolean hasUpper() {
        return upper != null;
    }

    private static <K> K requireBound(K key) {
        if (key == null) {
            throw new NullPointerException("range bound must not be null; use an unbounded factory instead");
        }
        return key;
    }

    @Override
    public String toString() {
        return (hasLower() ? (lowerInclusive ? "[" : "(") + lower : "(-inf")
                + ", "
                + (hasUpper() ? upper + (upperInclusive ? "]" : ")") : "+inf)");
    }
}
