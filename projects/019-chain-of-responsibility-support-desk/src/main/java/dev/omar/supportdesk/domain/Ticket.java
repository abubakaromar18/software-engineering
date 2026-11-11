package dev.omar.supportdesk.domain;

import java.util.Locale;
import java.util.Objects;

/**
 * An immutable support request. Handlers only read tickets; anything a handler concludes is
 * reported back through its {@code Decision}, never written onto the ticket.
 */
public record Ticket(String id, String customer, Category category, Severity severity,
                     String subject, String body) {

    public Ticket {
        id = requireText(id, "id");
        customer = requireText(customer, "customer");
        Objects.requireNonNull(category, "category");
        Objects.requireNonNull(severity, "severity");
        subject = requireText(subject, "subject");
        body = body == null ? "" : body.strip();
    }

    /** Subject and body, lower-cased, for keyword matching by handlers. */
    public String searchableText() {
        return (subject + "\n" + body).toLowerCase(Locale.ROOT);
    }

    private static String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("ticket " + field + " must not be blank");
        }
        return value.strip();
    }
}
