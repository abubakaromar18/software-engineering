package dev.omar.checkout.port;

import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Money;
import java.util.Objects;

/** A request to take money from a customer. The idempotency key makes retries safe. */
public record ChargeRequest(CustomerId customer, Money amount, String idempotencyKey) {

    public ChargeRequest {
        Objects.requireNonNull(customer, "customer");
        Objects.requireNonNull(amount, "amount");
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new IllegalArgumentException("idempotency key must not be blank");
        }
    }
}
