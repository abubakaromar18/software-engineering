package dev.omar.supportdesk.domain;

import java.util.Locale;

/** How badly the customer is affected. Declaration order is significant: later means more severe. */
public enum Severity {
    LOW,
    MEDIUM,
    HIGH,
    CRITICAL;

    /** True when this severity is no worse than {@code ceiling}; used for "handles up to X" rules. */
    public boolean atMost(Severity ceiling) {
        return compareTo(ceiling) <= 0;
    }

    /** Case-insensitive parse with an error message that lists the accepted values. */
    public static Severity parse(String raw) {
        try {
            return valueOf(raw.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException(
                    "unknown severity '" + raw + "' (expected one of LOW, MEDIUM, HIGH, CRITICAL)", e);
        }
    }
}
