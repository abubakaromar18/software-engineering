package dev.omar.checkout.port;

/** The payment provider could not be reached or timed out; the charge outcome is "did not happen". */
public class PaymentUnavailableException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public PaymentUnavailableException(String message) {
        super(message);
    }
}
