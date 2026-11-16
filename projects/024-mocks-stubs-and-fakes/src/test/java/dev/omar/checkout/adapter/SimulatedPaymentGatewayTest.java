package dev.omar.checkout.adapter;

import static dev.omar.checkout.Fixtures.ADA;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

import dev.omar.checkout.domain.Money;
import dev.omar.checkout.port.ChargeRequest;
import dev.omar.checkout.port.PaymentResult;
import org.junit.jupiter.api.Test;

/** A fake has real logic, so it needs its own tests. */
class SimulatedPaymentGatewayTest {

    private final SimulatedPaymentGateway gateway = new SimulatedPaymentGateway(Money.ofCents(50_00));

    @Test
    void approvesWithinTheLimitAndDeclinesAboveIt() {
        assertInstanceOf(PaymentResult.Approved.class, gateway.charge(new ChargeRequest(ADA, Money.ofCents(50_00), "k1")));
        assertInstanceOf(PaymentResult.Declined.class, gateway.charge(new ChargeRequest(ADA, Money.ofCents(50_01), "k2")));
        assertEquals(Money.ofCents(50_00), gateway.balance());
    }

    @Test
    void replayingAnIdempotencyKeyReturnsTheSameResultAndChargesOnce() {
        ChargeRequest request = new ChargeRequest(ADA, Money.ofCents(10_00), "same-key");

        PaymentResult first = gateway.charge(request);
        PaymentResult replay = gateway.charge(request);

        assertEquals(first, replay);
        assertEquals(Money.ofCents(10_00), gateway.balance());
    }

    @Test
    void refundRemovesTheChargeOnceAndRejectsUnknownOrRepeatedRefunds() {
        String tx = ((PaymentResult.Approved) gateway.charge(new ChargeRequest(ADA, Money.ofCents(5_00), "k"))).transactionId();

        gateway.refund(tx);

        assertEquals(Money.ZERO, gateway.balance());
        assertThrows(IllegalStateException.class, () -> gateway.refund(tx));
        assertThrows(IllegalArgumentException.class, () -> gateway.refund("ghost"));
    }
}
