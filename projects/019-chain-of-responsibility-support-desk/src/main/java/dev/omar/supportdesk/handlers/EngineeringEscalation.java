package dev.omar.supportdesk.handlers;

import dev.omar.supportdesk.chain.Decision;
import dev.omar.supportdesk.chain.SupportHandler;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;

/**
 * The catch-all at the end of the chain: anything nobody else took goes to engineering.
 *
 * <p>Tickets at or above the paging threshold page the on-call engineer; the rest become a bug report.
 * Ending the chain with an accept-everything handler is what guarantees no ticket is ever dropped.
 */
public final class EngineeringEscalation implements SupportHandler {

    private final String name;
    private final Severity pageAt;

    public EngineeringEscalation(String name, Severity pageAt) {
        this.name = name;
        this.pageAt = pageAt;
    }

    @Override
    public String name() {
        return name;
    }

    @Override
    public Decision handle(Ticket ticket) {
        if (pageAt.atMost(ticket.severity())) {
            return Decision.handled(Outcome.ESCALATED, "paged on-call engineer (" + ticket.severity() + ")");
        }
        return Decision.handled(Outcome.ESCALATED, "filed engineering bug report");
    }
}
