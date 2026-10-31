package dev.omar.pizza.store;

/** A well-formed request that this particular store does not offer (wrong size, off-menu item). */
public final class UnsupportedOrderException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public UnsupportedOrderException(String message) {
        super(message);
    }
}
