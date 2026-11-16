package dev.omar.checkout.port;

/** A payment provider's answer to a charge. Infrastructure failures are exceptions, not results. */
public sealed interface PaymentResult {

    record Approved(String transactionId) implements PaymentResult {}

    record Declined(String reason) implements PaymentResult {}
}
