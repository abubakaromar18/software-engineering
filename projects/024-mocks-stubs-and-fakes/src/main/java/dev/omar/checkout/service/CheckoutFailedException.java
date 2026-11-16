package dev.omar.checkout.service;

/**
 * An unexpected failure after money was taken (e.g. the order store is down). By the time this is
 * thrown the service has already refunded the payment and released the stock.
 */
public class CheckoutFailedException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public CheckoutFailedException(String message, Throwable cause) {
        super(message, cause);
    }
}
