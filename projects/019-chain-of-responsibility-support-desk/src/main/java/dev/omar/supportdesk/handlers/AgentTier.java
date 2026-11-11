package dev.omar.supportdesk.handlers;

import dev.omar.supportdesk.chain.Decision;
import dev.omar.supportdesk.chain.SupportHandler;
import dev.omar.supportdesk.domain.Category;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;

import java.util.EnumSet;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * A human support tier (Tier 1, Tier 2, …) that accepts tickets in its categories, up to a severity
 * ceiling, while it has queue capacity.
 *
 * <p>Tier 1 and Tier 2 differ only in data, so they are one class configured twice rather than two
 * near-identical subclasses. When the queue is full the tier passes, which is exactly the overflow
 * behaviour a support desk wants: the ticket moves to the next tier instead of waiting.
 */
public final class AgentTier implements SupportHandler {

    /** Capacity value meaning "no limit". */
    public static final int UNLIMITED = 0;

    private final String name;
    private final String displayName;
    private final Set<Category> categories;
    private final Severity maxSeverity;
    private final int capacity;
    private final AtomicInteger assigned = new AtomicInteger();

    public AgentTier(String name, String displayName, Set<Category> categories, Severity maxSeverity, int capacity) {
        if (categories.isEmpty()) {
            throw new IllegalArgumentException(name + ": an agent tier must cover at least one category");
        }
        if (capacity < 0) {
            throw new IllegalArgumentException(name + ": capacity must be >= 0 (0 = unlimited), got " + capacity);
        }
        this.name = name;
        this.displayName = displayName;
        this.categories = Set.copyOf(EnumSet.copyOf(categories));
        this.maxSeverity = maxSeverity;
        this.capacity = capacity;
    }

    @Override
    public String name() {
        return name;
    }

    @Override
    public Decision handle(Ticket ticket) {
        if (!categories.contains(ticket.category())) {
            return Decision.pass("category " + ticket.category() + " not covered");
        }
        if (!ticket.severity().atMost(maxSeverity)) {
            return Decision.pass("severity " + ticket.severity() + " above tier limit " + maxSeverity);
        }
        if (!tryReserveSlot()) {
            return Decision.pass("queue full (" + capacity + "/" + capacity + ")");
        }
        return Decision.handled(Outcome.ASSIGNED, "assigned to " + displayName + " queue");
    }

    /** Tickets this tier has accepted so far. */
    public int assignedCount() {
        return assigned.get();
    }

    /** Atomically claim a queue slot; safe if several threads push tickets through the same chain. */
    private boolean tryReserveSlot() {
        if (capacity == UNLIMITED) {
            assigned.incrementAndGet();
            return true;
        }
        int before = assigned.getAndUpdate(n -> n < capacity ? n + 1 : n);
        return before < capacity;
    }
}
