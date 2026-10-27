package dev.omar.money;

import java.io.Serializable;
import java.util.Objects;
import java.util.regex.Pattern;

/**
 * A currency as a value object: an ISO-4217-style code plus the number of minor-unit digits
 * (2 for USD cents, 0 for JPY, 3 for BHD fils).
 *
 * <p>Two currencies are equal when both code and fraction digits match, which a record gives
 * us for free. Use {@link #of(String)} for real ISO currencies; the canonical constructor is
 * public so non-ISO units (loyalty points, a test currency) can be modelled explicitly.
 *
 * @param code           three upper-case letters, e.g. {@code "USD"}
 * @param fractionDigits number of minor-unit digits, 0 to {@value #MAX_FRACTION_DIGITS}
 */
public record Currency(String code, int fractionDigits) implements Serializable {

    /** Upper bound that keeps {@code 10^fractionDigits} comfortably inside a {@code long}. */
    public static final int MAX_FRACTION_DIGITS = 9;

    private static final Pattern CODE = Pattern.compile("[A-Z]{3}");

    public static final Currency USD = of("USD");
    public static final Currency EUR = of("EUR");
    public static final Currency GBP = of("GBP");
    public static final Currency JPY = of("JPY");

    public Currency {
        Objects.requireNonNull(code, "code");
        if (!CODE.matcher(code).matches()) {
            throw new IllegalArgumentException("Currency code must be three upper-case letters: " + code);
        }
        if (fractionDigits < 0 || fractionDigits > MAX_FRACTION_DIGITS) {
            throw new IllegalArgumentException(
                    "fractionDigits must be between 0 and " + MAX_FRACTION_DIGITS + ": " + fractionDigits);
        }
    }

    /**
     * Looks up an ISO 4217 currency, taking its minor-unit digits from the JDK's currency data.
     *
     * @throws IllegalArgumentException if the code is unknown or has no defined minor unit (e.g. XAU)
     */
    public static Currency of(String code) {
        Objects.requireNonNull(code, "code");
        java.util.Currency iso;
        try {
            iso = java.util.Currency.getInstance(code);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Unknown ISO 4217 currency: " + code, e);
        }
        int digits = iso.getDefaultFractionDigits();
        if (digits < 0) {
            throw new IllegalArgumentException("Currency has no minor unit and cannot be used as money: " + code);
        }
        return new Currency(iso.getCurrencyCode(), digits);
    }

    @Override
    public String toString() {
        return code;
    }
}
