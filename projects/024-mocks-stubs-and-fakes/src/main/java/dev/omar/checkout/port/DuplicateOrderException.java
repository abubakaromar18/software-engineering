package dev.omar.checkout.port;

import dev.omar.checkout.domain.OrderId;

/** Raised when saving an order whose id is already stored. */
public class DuplicateOrderException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public DuplicateOrderException(OrderId id) {
        super("order already exists: " + id);
    }
}
