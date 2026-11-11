package dev.omar.supportdesk.domain;

import java.util.Arrays;
import java.util.Locale;
import java.util.stream.Collectors;

/** The area of the product a ticket is about. Agent tiers are configured with the categories they cover. */
public enum Category {
    ACCOUNT,
    BILLING,
    TECHNICAL,
    OTHER;

    /** Case-insensitive parse with an error message that lists the accepted values. */
    public static Category parse(String raw) {
        try {
            return valueOf(raw.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            String allowed = Arrays.stream(values()).map(Enum::name).collect(Collectors.joining(", "));
            throw new IllegalArgumentException(
                    "unknown category '" + raw + "' (expected one of " + allowed + ")", e);
        }
    }
}
