package dev.omar.checkout.domain;

import java.util.Objects;

/** Outcome of a checkout attempt. Sealed so callers handle both cases exhaustively. */
public sealed interface CheckoutResult {

    record Placed(Order order) implements CheckoutResult {
        public Placed {
            Objects.requireNonNull(order, "order");
        }
    }

    record Rejected(RejectionReason reason, String detail) implements CheckoutResult {
        public Rejected {
            Objects.requireNonNull(reason, "reason");
            Objects.requireNonNull(detail, "detail");
        }
    }
}
