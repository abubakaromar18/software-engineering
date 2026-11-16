package dev.omar.checkout.domain;

import java.util.regex.Pattern;

/** A stock-keeping unit code such as {@code BOOK-042}. Upper-case letters, digits and dashes only. */
public record Sku(String code) {

    private static final Pattern FORMAT = Pattern.compile("[A-Z0-9]+(-[A-Z0-9]+)*");

    public Sku {
        if (code == null || !FORMAT.matcher(code).matches()) {
            throw new IllegalArgumentException("invalid SKU: " + code);
        }
    }

    @Override
    public String toString() {
        return code;
    }
}
