package dev.omar.money;

import java.math.BigInteger;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Objects;
import java.util.stream.IntStream;

/**
 * Splits an integer quantity (minor units) by ratios without creating or losing any units.
 *
 * <p>Uses the largest-remainder (Hamilton) method: every part first gets
 * {@code floor(total * ratio / sum)}, then the few units left over go one at a time to the
 * parts with the largest fractional remainder. Ties go to the earlier part, so the result is
 * deterministic. Arithmetic is done in {@link BigInteger} so {@code total * ratio} cannot overflow.
 */
final class Allocator {

    private Allocator() {
    }

    /**
     * @param total  quantity to split; may be negative (it is split by magnitude, then negated)
     * @param ratios non-negative weights with a positive sum
     * @return one share per ratio, summing exactly to {@code total}
     */
    static long[] allocate(long total, long[] ratios) {
        Objects.requireNonNull(ratios, "ratios");
        if (ratios.length == 0) {
            throw new IllegalArgumentException("At least one ratio is required");
        }
        BigInteger ratioSum = BigInteger.ZERO;
        for (long ratio : ratios) {
            if (ratio < 0) {
                throw new IllegalArgumentException("Ratios must not be negative: " + Arrays.toString(ratios));
            }
            ratioSum = ratioSum.add(BigInteger.valueOf(ratio));
        }
        if (ratioSum.signum() == 0) {
            throw new IllegalArgumentException("At least one ratio must be positive");
        }

        // Work on the magnitude so rounding behaves the same for refunds as for charges.
        BigInteger magnitude = BigInteger.valueOf(total).abs();
        BigInteger[] shares = new BigInteger[ratios.length];
        BigInteger[] remainders = new BigInteger[ratios.length];
        BigInteger allocated = BigInteger.ZERO;
        for (int i = 0; i < ratios.length; i++) {
            BigInteger[] qr = magnitude.multiply(BigInteger.valueOf(ratios[i])).divideAndRemainder(ratioSum);
            shares[i] = qr[0];
            remainders[i] = qr[1];
            allocated = allocated.add(qr[0]);
        }

        // Fewer than ratios.length units are left, and only parts with a positive remainder get one.
        int leftover = magnitude.subtract(allocated).intValueExact();
        int[] byRemainderDesc = IntStream.range(0, ratios.length)
                .boxed()
                .sorted(Comparator.<Integer, BigInteger>comparing(i -> remainders[i]).reversed()
                        .thenComparing(Comparator.naturalOrder()))
                .mapToInt(Integer::intValue)
                .limit(leftover)
                .toArray();
        for (int i : byRemainderDesc) {
            shares[i] = shares[i].add(BigInteger.ONE);
        }

        long[] result = new long[ratios.length];
        for (int i = 0; i < ratios.length; i++) {
            BigInteger signed = total < 0 ? shares[i].negate() : shares[i];
            result[i] = signed.longValueExact();
        }
        return result;
    }
}
