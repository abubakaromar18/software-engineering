package dev.omar.supportdesk.audit;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class InMemoryAuditTrailTest {

    private static final Instant AT = Instant.parse("2026-11-11T09:00:00Z");

    @Test
    void entriesAreAnImmutableSnapshotInRecordingOrder() {
        InMemoryAuditTrail trail = new InMemoryAuditTrail();
        AuditEntry first = new AuditEntry(AT, "T-1", "spam", AuditStep.PASSED, "clean");
        trail.record(first);

        List<AuditEntry> snapshot = trail.entries();
        trail.record(new AuditEntry(AT, "T-2", "spam", AuditStep.HANDLED, "REJECTED: spam"));

        assertEquals(List.of(first), snapshot);
        assertThrows(UnsupportedOperationException.class, () -> snapshot.add(first));
        assertEquals(2, trail.entries().size());
    }

    @Test
    void entriesForFiltersByTicket() {
        InMemoryAuditTrail trail = new InMemoryAuditTrail();
        trail.record(new AuditEntry(AT, "T-1", "a", AuditStep.PASSED, "x"));
        trail.record(new AuditEntry(AT, "T-2", "a", AuditStep.PASSED, "y"));
        trail.record(new AuditEntry(AT, "T-1", "b", AuditStep.HANDLED, "z"));

        assertEquals(List.of("a", "b"), trail.entriesFor("T-1").stream().map(AuditEntry::handler).toList());
    }

    @Test
    void formatIsASingleAlignedLine() {
        AuditEntry entry = new AuditEntry(AT, "T-1", "faq", AuditStep.PASSED, "no FAQ match");
        assertEquals("2026-11-11T09:00:00Z  T-1      faq            PASSED    no FAQ match", entry.format());
    }
}
