package dev.omar.checkout.domain;

/** Opaque identifier of the customer placing an order. */
public record CustomerId(String value) {

    public CustomerId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("customer id must not be blank");
        }
    }

    @Override
    public String toString() {
        return value;
    }
}
