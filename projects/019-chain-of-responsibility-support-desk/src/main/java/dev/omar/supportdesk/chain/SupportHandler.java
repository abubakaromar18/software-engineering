package dev.omar.supportdesk.chain;

import dev.omar.supportdesk.domain.Ticket;

/**
 * One link in the support chain.
 *
 * <p>Handlers deliberately know nothing about the handler after them: there is no {@code next}
 * field and no {@code super.handle()} call to forget. They only decide "mine" or "not mine, because…",
 * and {@link SupportChain} owns ordering, forwarding, error isolation and auditing. That keeps each
 * handler a small, independently testable rule, and lets configuration reorder them freely.
 */
public interface SupportHandler {

    /** Stable name used in configuration, audit entries and resolutions. */
    String name();

    /** Decide what to do with {@code ticket}. Must not return {@code null}. */
    Decision handle(Ticket ticket);
}
