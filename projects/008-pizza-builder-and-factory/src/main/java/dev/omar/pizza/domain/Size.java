package dev.omar.pizza.domain;

import java.math.BigDecimal;
import java.util.Locale;

/** Pizza sizes. Every ingredient price is scaled by the size's multiplier. */
public enum Size {
    SMALL(25, "1.00"),
    MEDIUM(30, "1.25"),
    LARGE(35, "1.50");

    private final int diameterCm;
    private final BigDecimal priceMultiplier;

    Size(int diameterCm, String priceMultiplier) {
        this.diameterCm = diameterCm;
        this.priceMultiplier = new BigDecimal(priceMultiplier);
    }

    public int diameterCm() {
        return diameterCm;
    }

    public BigDecimal priceMultiplier() {
        return priceMultiplier;
    }

    public String displayName() {
        return name().charAt(0) + name().substring(1).toLowerCase(Locale.ROOT);
    }

    /** Case-insensitive lookup that also accepts the first letter: {@code "l"} is {@code LARGE}. */
    public static Size parse(String text) {
        String key = text.trim().toUpperCase(Locale.ROOT);
        for (Size size : values()) {
            if (size.name().equals(key) || size.name().substring(0, 1).equals(key)) {
                return size;
            }
        }
        throw new IllegalArgumentException("Unknown size '" + text + "'. Expected small, medium or large.");
    }
}
