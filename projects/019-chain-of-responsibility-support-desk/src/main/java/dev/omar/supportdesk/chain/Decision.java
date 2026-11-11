package dev.omar.supportdesk.chain;

import dev.omar.supportdesk.domain.Outcome;

import java.util.Objects;

/**
 * A handler's answer for one ticket: either it takes the ticket, or it passes and says why.
 *
 * <p>Sealed, so the chain's {@code switch} over decisions is exhaustive and checked by the compiler.
 * Requiring a reason on {@link Pass} is what makes the audit trail useful: it records not only who
 * handled a ticket but why every earlier handler declined it.
 */
public sealed interface Decision {

    /** The handler accepted the ticket; the chain stops here. */
    record Handled(Outcome outcome, String message) implements Decision {
        public Handled {
            Objects.requireNonNull(outcome, "outcome");
            Objects.requireNonNull(message, "message");
            if (outcome == Outcome.UNHANDLED) {
                throw new IllegalArgumentException("a handler cannot 'handle' a ticket as UNHANDLED; pass instead");
            }
        }
    }

    /** The handler declined; the chain moves on to the next handler. */
    record Pass(String reason) implements Decision {
        public Pass {
            Objects.requireNonNull(reason, "reason");
        }
    }

    static Decision handled(Outcome outcome, String message) {
        return new Handled(outcome, message);
    }

    static Decision pass(String reason) {
        return new Pass(reason);
    }
}
