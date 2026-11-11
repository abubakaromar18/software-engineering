package dev.omar.supportdesk.audit;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/** Thread-safe, in-memory audit trail. Callers get snapshots, so they can never edit history. */
public final class InMemoryAuditTrail implements AuditTrail {

    private final List<AuditEntry> entries = new ArrayList<>();

    @Override
    public synchronized void record(AuditEntry entry) {
        entries.add(Objects.requireNonNull(entry, "entry"));
    }

    @Override
    public synchronized List<AuditEntry> entries() {
        return List.copyOf(entries);
    }
}
