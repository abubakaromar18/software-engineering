package dev.omar.money;

import java.io.Serializable;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.NumberFormat;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.stream.Collector;

/**
 * An immutable amount of money in a single currency.
 *
 * <p>The amount is stored as a whole number of minor units (cents, pence, yen), so addition,
 * subtraction and multiplication by integers are exact, and any overflow throws instead of
 * wrapping around. Equality is by value: {@code Money.of("1.0", USD)} equals
 * {@code Money.of("1.00", USD)}, unlike {@link BigDecimal#equals}.
 *
 * <p>There is deliberately no {@code dividedBy}: dividing money leaks or invents cents. Use
 * {@link #allocate(long...)} or {@link #split(int)}, which always add back up to the original.
 * Operations that must round (scaling by a decimal factor) require an explicit
 * {@link RoundingMode}.
 *
 * @param minorUnits amount in the currency's smallest unit, e.g. 1234 for USD 12.34
 * @param currency   currency of the amount
 */
public record Money(long minorUnits, Currency currency) implements Comparable<Money>, Serializable {

    public Money {
        Objects.requireNonNull(currency, "currency");
    }

    // ---- Factories -------------------------------------------------------------------------

    /** Creates an amount from minor units, e.g. {@code ofMinor(1234, USD)} is USD 12.34. */
    public static Money ofMinor(long minorUnits, Currency currency) {
        return new Money(minorUnits, currency);
    }

    /** Zero in the given currency. */
    public static Money zero(Currency currency) {
        return new Money(0, currency);
    }

    /**
     * Creates an amount from a decimal that must fit the currency's precision exactly.
     *
     * @throws ArithmeticException if the amount has more decimals than the currency allows
     *                             (e.g. USD 0.001) or does not fit in a {@code long}
     */
    public static Money of(BigDecimal amount, Currency currency) {
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        BigDecimal scaled;
        try {
            scaled = amount.setScale(currency.fractionDigits(), RoundingMode.UNNECESSARY);
        } catch (ArithmeticException e) {
            throw new ArithmeticException(
                    amount.toPlainString() + " has more than " + currency.fractionDigits()
                            + " decimal places allowed for " + currency + "; pass a RoundingMode to round it");
        }
        return new Money(scaled.unscaledValue().longValueExact(), currency);
    }

    /** Creates an amount from a decimal, rounding to the currency's precision with {@code rounding}. */
    public static Money of(BigDecimal amount, Currency currency, RoundingMode rounding) {
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        Objects.requireNonNull(rounding, "rounding");
        BigDecimal scaled = amount.setScale(currency.fractionDigits(), rounding);
        return new Money(scaled.unscaledValue().longValueExact(), currency);
    }

    /** Convenience for {@link #of(BigDecimal, Currency)} with a decimal string such as {@code "12.34"}. */
    public static Money of(String amount, Currency currency) {
        Objects.requireNonNull(amount, "amount");
        return of(new BigDecimal(amount), currency);
    }

    /**
     * Parses the format produced by {@link #toString()}, e.g. {@code "USD 12.34"}.
     *
     * @throws IllegalArgumentException if the text is not {@code "<CODE> <amount>"}
     */
    public static Money parse(String text) {
        Objects.requireNonNull(text, "text");
        String[] parts = text.trim().split("\\s+");
        if (parts.length != 2) {
            throw new IllegalArgumentException("Expected '<CODE> <amount>' but got: " + text);
        }
        BigDecimal amount;
        try {
            amount = new BigDecimal(parts[1]);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Invalid amount in: " + text, e);
        }
        return of(amount, Currency.of(parts[0]));
    }

    // ---- Queries -----------------------------------------------------------------------------

    /** The amount as a decimal with exactly the currency's scale, e.g. {@code 12.30} for USD. */
    public BigDecimal amount() {
        return BigDecimal.valueOf(minorUnits, currency.fractionDigits());
    }

    public boolean isZero() {
        return minorUnits == 0;
    }

    public boolean isPositive() {
        return minorUnits > 0;
    }

    public boolean isNegative() {
        return minorUnits < 0;
    }

    public boolean isGreaterThan(Money other) {
        return compareTo(other) > 0;
    }

    public boolean isLessThan(Money other) {
        return compareTo(other) < 0;
    }

    /**
     * Orders amounts of the same currency. Comparing different currencies is meaningless
     * without an exchange rate, so it throws rather than picking an arbitrary order.
     *
     * @throws CurrencyMismatchException if the currencies differ
     */
    @Override
    public int compareTo(Money other) {
        requireSameCurrency(other);
        return Long.compare(minorUnits, other.minorUnits);
    }

    // ---- Arithmetic --------------------------------------------------------------------------

    public Money plus(Money other) {
        requireSameCurrency(other);
        return withMinor(Math.addExact(minorUnits, other.minorUnits));
    }

    public Money minus(Money other) {
        requireSameCurrency(other);
        return withMinor(Math.subtractExact(minorUnits, other.minorUnits));
    }

    public Money negated() {
        return withMinor(Math.negateExact(minorUnits));
    }

    public Money abs() {
        return isNegative() ? negated() : this;
    }

    /** Exact multiplication by a whole number, e.g. quantity times unit price. */
    public Money times(long multiplier) {
        return withMinor(Math.multiplyExact(minorUnits, multiplier));
    }

    /**
     * Multiplies by a decimal factor (tax rate, discount, exchange rate) and rounds the result
     * back to the currency's precision. The caller chooses the rounding mode, because the
     * right one is a business rule (banks often use HALF_EVEN, tax authorities HALF_UP).
     */
    public Money times(BigDecimal factor, RoundingMode rounding) {
        Objects.requireNonNull(factor, "factor");
        return of(amount().multiply(factor), currency, rounding);
    }

    /**
     * Splits this amount by ratios so that the parts add up to exactly this amount.
     * {@code USD 0.05.allocate(3, 7)} gives {@code [USD 0.02, USD 0.03]}; the odd cent goes to
     * the part whose exact share was cut the most (largest-remainder method).
     *
     * @param ratios non-negative weights, at least one positive
     */
    public List<Money> allocate(long... ratios) {
        return Arrays.stream(Allocator.allocate(minorUnits, ratios))
                .mapToObj(this::withMinor)
                .toList();
    }

    /** Splits into {@code parts} near-equal amounts; earlier parts receive any extra minor unit. */
    public List<Money> split(int parts) {
        if (parts <= 0) {
            throw new IllegalArgumentException("parts must be positive: " + parts);
        }
        long[] ratios = new long[parts];
        Arrays.fill(ratios, 1);
        return allocate(ratios);
    }

    // ---- Aggregation -------------------------------------------------------------------------

    /**
     * Sums amounts that must all be in {@code currency}; an empty input sums to zero, which is
     * why the currency has to be given up front.
     */
    public static Money sum(Currency currency, Iterable<Money> amounts) {
        Money total = zero(currency);
        for (Money amount : amounts) {
            total = total.plus(amount);
        }
        return total;
    }

    /** A stream collector equivalent to {@link #sum(Currency, Iterable)}. */
    public static Collector<Money, ?, Money> summing(Currency currency) {
        Objects.requireNonNull(currency, "currency");
        return Collector.of(
                () -> new Money[] {zero(currency)},
                (acc, amount) -> acc[0] = acc[0].plus(amount),
                (left, right) -> {
                    left[0] = left[0].plus(right[0]);
                    return left;
                },
                acc -> acc[0]);
    }

    // ---- Presentation ------------------------------------------------------------------------

    /** Locale-aware display text, e.g. {@code "$1,234.50"} for en-US. Not meant for parsing. */
    public String format(Locale locale) {
        Objects.requireNonNull(locale, "locale");
        java.util.Currency iso;
        try {
            iso = java.util.Currency.getInstance(currency.code());
        } catch (IllegalArgumentException notIso) {
            // Custom units (loyalty points etc.) have no symbol; fall back to the stable form.
            return toString();
        }
        NumberFormat format = NumberFormat.getCurrencyInstance(locale);
        format.setCurrency(iso);
        format.setMinimumFractionDigits(currency.fractionDigits());
        format.setMaximumFractionDigits(currency.fractionDigits());
        return format.format(amount());
    }

    /** Stable, locale-independent text such as {@code "USD 12.34"}; round-trips via {@link #parse}. */
    @Override
    public String toString() {
        return currency.code() + " " + amount().toPlainString();
    }

    // ---- Internals ---------------------------------------------------------------------------

    private Money withMinor(long newMinorUnits) {
        return new Money(newMinorUnits, currency);
    }

    private void requireSameCurrency(Money other) {
        Objects.requireNonNull(other, "other");
        if (!currency.equals(other.currency)) {
            throw new CurrencyMismatchException(currency, other.currency);
        }
    }
}
