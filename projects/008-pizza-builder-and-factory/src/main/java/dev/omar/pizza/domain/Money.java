package dev.omar.pizza.domain;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * An amount of US dollars held as whole cents, so prices never pick up floating-point error.
 *
 * <p>Kept deliberately small: project 004 covers money in depth. Here it only needs to add,
 * multiply and print.
 */
public record Money(long cents) implements Comparable<Money> {

    public static final Money ZERO = new Money(0);

    public Money {
        if (cents < 0) {
            throw new IllegalArgumentException("Money cannot be negative: " + cents + " cents");
        }
    }

    public static Money ofCents(long cents) {
        return new Money(cents);
    }

    /** Parses a dollar string such as {@code "12.50"}. More than two decimal places is rejected. */
    public static Money of(String dollars) {
        BigDecimal amount = new BigDecimal(dollars);
        try {
            return new Money(amount.movePointRight(2).longValueExact());
        } catch (ArithmeticException e) {
            throw new IllegalArgumentException("Not a whole number of cents: " + dollars, e);
        }
    }

    public Money plus(Money other) {
        return new Money(Math.addExact(cents, other.cents));
    }

    public Money times(int quantity) {
        return new Money(Math.multiplyExact(cents, (long) quantity));
    }

    /** Multiplies by a decimal factor (a size multiplier, a tax rate) using banker's rounding. */
    public Money times(BigDecimal factor) {
        BigDecimal result = BigDecimal.valueOf(cents).multiply(factor).setScale(0, RoundingMode.HALF_EVEN);
        return new Money(result.longValueExact());
    }

    @Override
    public int compareTo(Money other) {
        return Long.compare(cents, other.cents);
    }

    @Override
    public String toString() {
        return String.format("$%d.%02d", cents / 100, cents % 100);
    }
}
