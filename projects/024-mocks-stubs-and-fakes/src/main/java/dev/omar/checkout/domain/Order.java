package dev.omar.checkout.domain;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

/** A confirmed, paid order. Immutable; the total is derived from its lines. */
public record Order(OrderId id, CustomerId customer, List<OrderLine> lines, Instant placedAt, String paymentTransactionId) {

    public Order {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(customer, "customer");
        Objects.requireNonNull(placedAt, "placedAt");
        lines = List.copyOf(lines);
        if (lines.isEmpty()) {
            throw new IllegalArgumentException("an order needs at least one line");
        }
        if (paymentTransactionId == null || paymentTransactionId.isBlank()) {
            throw new IllegalArgumentException("payment transaction id must not be blank");
        }
    }

    public Money total() {
        return lines.stream().map(OrderLine::lineTotal).reduce(Money.ZERO, Money::plus);
    }
}
