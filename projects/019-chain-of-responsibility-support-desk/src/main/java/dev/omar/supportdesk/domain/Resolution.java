package dev.omar.supportdesk.domain;

import java.util.Objects;

/** What the chain did with one ticket: who took it, the outcome, and a message for the customer or log. */
public record Resolution(String ticketId, Outcome outcome, String handledBy, String message) {

    public Resolution {
        Objects.requireNonNull(ticketId, "ticketId");
        Objects.requireNonNull(outcome, "outcome");
        Objects.requireNonNull(handledBy, "handledBy");
        Objects.requireNonNull(message, "message");
    }
}
