package dev.omar.supportdesk.domain;

/** The final state of a ticket after it has been through the chain. */
public enum Outcome {
    /** Discarded before any human saw it (spam, abuse). */
    REJECTED,
    /** Answered automatically, e.g. from the FAQ knowledge base. */
    AUTO_RESOLVED,
    /** Placed in a human agent tier's queue. */
    ASSIGNED,
    /** Handed to engineering; the support desk no longer owns it. */
    ESCALATED,
    /** No handler accepted the ticket. A well-configured chain ends with a catch-all so this is rare. */
    UNHANDLED
}
