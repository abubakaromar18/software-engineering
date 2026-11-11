package dev.omar.supportdesk.audit;

import java.time.Instant;
import java.util.Objects;

/** One immutable line of the audit trail. */
public record AuditEntry(Instant at, String ticketId, String handler, AuditStep step, String note) {

    public AuditEntry {
        Objects.requireNonNull(at, "at");
        Objects.requireNonNull(ticketId, "ticketId");
        Objects.requireNonNull(handler, "handler");
        Objects.requireNonNull(step, "step");
        Objects.requireNonNull(note, "note");
    }

    /** Single-line, human-readable form, e.g. {@code 2026-11-11T09:00:00Z T-1 faq-bot PASSED no FAQ match}. */
    public String format() {
        return "%s  %-8s %-14s %-9s %s".formatted(at, ticketId, handler, step, note);
    }
}
