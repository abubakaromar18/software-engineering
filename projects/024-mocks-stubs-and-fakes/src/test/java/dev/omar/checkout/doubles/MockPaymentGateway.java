package dev.omar.checkout.doubles;

import dev.omar.checkout.port.ChargeRequest;
import dev.omar.checkout.port.PaymentGateway;
import dev.omar.checkout.port.PaymentResult;
import java.util.ArrayDeque;
import java.util.Deque;

/**
 * MOCK — pre-programmed with the exact calls it expects, in order. Any unexpected call fails
 * immediately (with a stack trace pointing at the offending line of production code), and
 * {@link #verify()} fails if an expected call never happened. This is behaviour verification:
 * the test <em>is</em> the specification of the conversation with the collaborator.
 *
 * <p>Written by hand so the mechanics are visible; Mockito's {@code verify} does the same job.
 */
public final class MockPaymentGateway implements PaymentGateway {

    private sealed interface Expectation {}

    private record ExpectCharge(ChargeRequest request, PaymentResult result) implements Expectation {}

    private record ExpectRefund(String transactionId) implements Expectation {}

    private final Deque<Expectation> expected = new ArrayDeque<>();

    public MockPaymentGateway expectCharge(ChargeRequest request, PaymentResult result) {
        expected.add(new ExpectCharge(request, result));
        return this;
    }

    public MockPaymentGateway expectRefund(String transactionId) {
        expected.add(new ExpectRefund(transactionId));
        return this;
    }

    @Override
    public PaymentResult charge(ChargeRequest request) {
        if (expected.peek() instanceof ExpectCharge(ChargeRequest wanted, PaymentResult result)) {
            if (!wanted.equals(request)) {
                throw new AssertionError("charge called with " + request + " but expected " + wanted);
            }
            expected.remove();
            return result;
        }
        throw new AssertionError("unexpected charge(" + request + "); next expectation: " + describeNext());
    }

    @Override
    public void refund(String transactionId) {
        if (expected.peek() instanceof ExpectRefund(String wanted)) {
            if (!wanted.equals(transactionId)) {
                throw new AssertionError("refund called with " + transactionId + " but expected " + wanted);
            }
            expected.remove();
            return;
        }
        throw new AssertionError("unexpected refund(" + transactionId + "); next expectation: " + describeNext());
    }

    /** Fails if any expected call was not made. Call at the end of the test. */
    public void verify() {
        if (!expected.isEmpty()) {
            throw new AssertionError("expected calls never made: " + expected);
        }
    }

    private String describeNext() {
        return expected.isEmpty() ? "none" : expected.peek().toString();
    }
}
