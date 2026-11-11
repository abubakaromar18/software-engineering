package dev.omar.supportdesk;

import dev.omar.supportdesk.domain.Category;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

/** Test fixtures shared across packages. */
public final class Tickets {

    public static final Clock FIXED_CLOCK = Clock.fixed(Instant.parse("2026-11-11T09:00:00Z"), ZoneOffset.UTC);

    private Tickets() {
    }

    public static Ticket ticket(String id, Category category, Severity severity, String subject) {
        return new Ticket(id, "customer@example.com", category, severity, subject, "");
    }

    public static Ticket ticket(Category category, Severity severity) {
        return ticket("T-1", category, severity, "Something is wrong");
    }
}
