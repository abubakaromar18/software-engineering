package dev.omar.supportdesk.chain;

import dev.omar.supportdesk.audit.AuditEntry;
import dev.omar.supportdesk.audit.AuditStep;
import dev.omar.supportdesk.audit.AuditTrail;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Resolution;
import dev.omar.supportdesk.domain.Ticket;

import java.time.Clock;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Runs a ticket through an ordered list of handlers until one accepts it.
 *
 * <p>This is the "pipeline" flavour of Chain of Responsibility: the chain object, not each handler,
 * forwards the request. Centralising the loop buys three things the linked-list flavour would make
 * every handler re-implement:
 * <ul>
 *   <li><b>Auditing</b> — every pass, failure and final decision is recorded in one place;</li>
 *   <li><b>Fault isolation</b> — a handler that throws is logged as {@link AuditStep#FAILED} and skipped,
 *       so one broken rule cannot lose a customer's ticket;</li>
 *   <li><b>Configurable order</b> — the list comes from configuration and handlers never reference each other.</li>
 * </ul>
 */
public final class SupportChain {

    /** Name used in audit entries and resolutions when no handler accepted the ticket. */
    public static final String END_OF_CHAIN = "end-of-chain";

    private final List<SupportHandler> handlers;
    private final AuditTrail audit;
    private final Clock clock;

    public SupportChain(List<SupportHandler> handlers, AuditTrail audit, Clock clock) {
        this.handlers = List.copyOf(handlers);
        this.audit = Objects.requireNonNull(audit, "audit");
        this.clock = Objects.requireNonNull(clock, "clock");
        validate(this.handlers);
    }

    /** Process one ticket. Always returns a resolution; never throws because of a handler. */
    public Resolution process(Ticket ticket) {
        Objects.requireNonNull(ticket, "ticket");
        for (SupportHandler handler : handlers) {
            Decision decision;
            try {
                decision = Objects.requireNonNull(handler.handle(ticket), "handler returned null");
            } catch (RuntimeException e) {
                record(ticket, handler.name(), AuditStep.FAILED, e.getClass().getSimpleName() + ": " + e.getMessage());
                continue;
            }
            switch (decision) {
                case Decision.Handled handled -> {
                    record(ticket, handler.name(), AuditStep.HANDLED, handled.outcome() + ": " + handled.message());
                    return new Resolution(ticket.id(), handled.outcome(), handler.name(), handled.message());
                }
                case Decision.Pass pass -> record(ticket, handler.name(), AuditStep.PASSED, pass.reason());
            }
        }
        String message = "no handler accepted the ticket";
        record(ticket, END_OF_CHAIN, AuditStep.UNHANDLED, message);
        return new Resolution(ticket.id(), Outcome.UNHANDLED, END_OF_CHAIN, message);
    }

    /** Process tickets in order; convenience for batch input such as the CLI's CSV file. */
    public List<Resolution> processAll(List<Ticket> tickets) {
        return tickets.stream().map(this::process).toList();
    }

    /** Handler names in chain order, e.g. for printing the active configuration. */
    public List<String> handlerNames() {
        return handlers.stream().map(SupportHandler::name).toList();
    }

    private void record(Ticket ticket, String handler, AuditStep step, String note) {
        audit.record(new AuditEntry(clock.instant(), ticket.id(), handler, step, note));
    }

    private static void validate(List<SupportHandler> handlers) {
        if (handlers.isEmpty()) {
            throw new IllegalArgumentException("a support chain needs at least one handler");
        }
        Set<String> seen = new HashSet<>();
        for (SupportHandler handler : handlers) {
            if (!seen.add(handler.name())) {
                // Duplicate names would make the audit trail ambiguous.
                throw new IllegalArgumentException("duplicate handler name in chain: " + handler.name());
            }
        }
    }
}
