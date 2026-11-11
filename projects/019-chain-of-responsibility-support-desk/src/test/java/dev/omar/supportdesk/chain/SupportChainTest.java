package dev.omar.supportdesk.chain;

import dev.omar.supportdesk.audit.AuditEntry;
import dev.omar.supportdesk.audit.AuditStep;
import dev.omar.supportdesk.audit.InMemoryAuditTrail;
import dev.omar.supportdesk.domain.Category;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Resolution;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

import static dev.omar.supportdesk.Tickets.FIXED_CLOCK;
import static dev.omar.supportdesk.Tickets.ticket;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SupportChainTest {

    private final InMemoryAuditTrail audit = new InMemoryAuditTrail();
    private final List<String> visited = new ArrayList<>();

    /** A handler that records it was visited and then applies {@code rule}. */
    private SupportHandler handler(String name, Function<Ticket, Decision> rule) {
        return new SupportHandler() {
            @Override
            public String name() {
                return name;
            }

            @Override
            public Decision handle(Ticket ticket) {
                visited.add(name);
                return rule.apply(ticket);
            }
        };
    }

    private SupportChain chain(SupportHandler... handlers) {
        return new SupportChain(List.of(handlers), audit, FIXED_CLOCK);
    }

    @Test
    void firstHandlerThatAcceptsWinsAndLaterHandlersAreNotVisited() {
        SupportChain chain = chain(
                handler("a", t -> Decision.pass("not mine")),
                handler("b", t -> Decision.handled(Outcome.ASSIGNED, "b took it")),
                handler("c", t -> Decision.handled(Outcome.ESCALATED, "never reached")));

        Resolution resolution = chain.process(ticket(Category.BILLING, Severity.LOW));

        assertEquals(new Resolution("T-1", Outcome.ASSIGNED, "b", "b took it"), resolution);
        assertEquals(List.of("a", "b"), visited);
    }

    @Test
    void auditTrailRecordsEveryHopWithReasons() {
        SupportChain chain = chain(
                handler("a", t -> Decision.pass("wrong category")),
                handler("b", t -> Decision.handled(Outcome.ASSIGNED, "queued")));

        chain.process(ticket(Category.BILLING, Severity.LOW));

        assertEquals(List.of(
                new AuditEntry(FIXED_CLOCK.instant(), "T-1", "a", AuditStep.PASSED, "wrong category"),
                new AuditEntry(FIXED_CLOCK.instant(), "T-1", "b", AuditStep.HANDLED, "ASSIGNED: queued")),
                audit.entries());
    }

    @Test
    void throwingHandlerIsAuditedAndSkippedSoTheTicketIsNotLost() {
        SupportChain chain = chain(
                handler("broken", t -> {
                    throw new IllegalStateException("knowledge base offline");
                }),
                handler("backup", t -> Decision.handled(Outcome.ASSIGNED, "ok")));

        Resolution resolution = chain.process(ticket(Category.ACCOUNT, Severity.LOW));

        assertEquals("backup", resolution.handledBy());
        AuditEntry failure = audit.entries().get(0);
        assertEquals(AuditStep.FAILED, failure.step());
        assertEquals("IllegalStateException: knowledge base offline", failure.note());
    }

    @Test
    void nullDecisionIsTreatedAsAFailure() {
        SupportChain chain = chain(
                handler("sloppy", t -> null),
                handler("backup", t -> Decision.handled(Outcome.ASSIGNED, "ok")));

        chain.process(ticket(Category.ACCOUNT, Severity.LOW));

        assertEquals(AuditStep.FAILED, audit.entries().get(0).step());
    }

    @Test
    void reachingTheEndOfTheChainYieldsUnhandledAndAnAuditEntry() {
        SupportChain chain = chain(handler("a", t -> Decision.pass("no")));

        Resolution resolution = chain.process(ticket(Category.OTHER, Severity.LOW));

        assertEquals(Outcome.UNHANDLED, resolution.outcome());
        assertEquals(SupportChain.END_OF_CHAIN, resolution.handledBy());
        AuditEntry last = audit.entries().get(audit.entries().size() - 1);
        assertEquals(AuditStep.UNHANDLED, last.step());
    }

    @Test
    void processAllKeepsInputOrderAndAuditSeparatesTickets() {
        SupportChain chain = chain(handler("only", t -> Decision.handled(Outcome.ASSIGNED, t.id())));

        List<Resolution> results = chain.processAll(List.of(
                ticket("T-1", Category.ACCOUNT, Severity.LOW, "x"),
                ticket("T-2", Category.ACCOUNT, Severity.LOW, "y")));

        assertEquals(List.of("T-1", "T-2"), results.stream().map(Resolution::message).toList());
        assertEquals(1, audit.entriesFor("T-2").size());
    }

    @Test
    void rejectsEmptyChainAndDuplicateNames() {
        assertThrows(IllegalArgumentException.class, () -> new SupportChain(List.of(), audit, FIXED_CLOCK));
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class, () -> chain(
                handler("x", t -> Decision.pass("")), handler("x", t -> Decision.pass(""))));
        assertTrue(e.getMessage().contains("duplicate"));
    }

    @Test
    void handlersCannotClaimToHandleATicketAsUnhandled() {
        assertThrows(IllegalArgumentException.class, () -> Decision.handled(Outcome.UNHANDLED, "?"));
    }
}
