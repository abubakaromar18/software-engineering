package dev.omar.checkout.port;

/** Outbound port to a payment provider (the real one is a third-party HTTP API, never called in tests). */
public interface PaymentGateway {

    /**
     * Charges the customer.
     *
     * @throws PaymentUnavailableException if the provider cannot be reached
     */
    PaymentResult charge(ChargeRequest request);

    /** Reverses an approved charge in full. */
    void refund(String transactionId);
}
