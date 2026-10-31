package dev.omar.pizza.order;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Settings read from the environment. Taking a {@code Map} instead of calling
 * {@code System.getenv()} directly keeps it testable.
 */
public record ShopConfig(BigDecimal taxRate) {

    public static final String TAX_RATE_VARIABLE = "PIZZA_TAX_RATE";
    public static final BigDecimal DEFAULT_TAX_RATE = new BigDecimal("0.0825");

    public static ShopConfig fromEnvironment(Map<String, String> env) {
        String raw = env.get(TAX_RATE_VARIABLE);
        if (raw == null || raw.isBlank()) {
            return new ShopConfig(DEFAULT_TAX_RATE);
        }
        try {
            BigDecimal rate = new BigDecimal(raw.trim());
            if (rate.signum() < 0 || rate.compareTo(BigDecimal.ONE) >= 0) {
                throw new IllegalArgumentException(TAX_RATE_VARIABLE + " must be in [0, 1), e.g. 0.0825; got " + raw);
            }
            return new ShopConfig(rate);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(TAX_RATE_VARIABLE + " is not a number: " + raw, e);
        }
    }
}
