package dev.omar.checkout.domain;

/** Identifier of a placed order; also used as the payment idempotency key. */
public record OrderId(String value) {

    public OrderId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("order id must not be blank");
        }
    }

    @Override
    public String toString() {
        return value;
    }
}
