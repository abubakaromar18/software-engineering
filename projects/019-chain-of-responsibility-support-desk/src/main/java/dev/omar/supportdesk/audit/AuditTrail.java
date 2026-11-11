package dev.omar.supportdesk.audit;

import java.util.List;

/**
 * Append-only record of every decision the chain makes.
 *
 * <p>An interface so the chain does not care where entries go: memory for tests and the CLI, but a
 * database table or log shipper in a real deployment would implement the same two methods.
 */
public interface AuditTrail {

    void record(AuditEntry entry);

    /** All entries in the order they were recorded. */
    List<AuditEntry> entries();

    /** The journey of one ticket, in order. */
    default List<AuditEntry> entriesFor(String ticketId) {
        return entries().stream().filter(e -> e.ticketId().equals(ticketId)).toList();
    }
}
