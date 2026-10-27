package dev.omar.money;

/**
 * Thrown when an operation combines or compares amounts in different currencies.
 * Converting between currencies needs an exchange rate, so it is never done implicitly.
 */
public final class CurrencyMismatchException extends IllegalArgumentException {

    private static final long serialVersionUID = 1L;

    private final Currency expected;
    private final Currency actual;

    public CurrencyMismatchException(Currency expected, Currency actual) {
        super("Currency mismatch: expected " + expected + " but got " + actual);
        this.expected = expected;
        this.actual = actual;
    }

    public Currency expected() {
        return expected;
    }

    public Currency actual() {
        return actual;
    }
}
