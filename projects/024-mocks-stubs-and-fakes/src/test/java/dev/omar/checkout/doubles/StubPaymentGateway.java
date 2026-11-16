package dev.omar.checkout.doubles;

import dev.omar.checkout.port.ChargeRequest;
import dev.omar.checkout.port.PaymentGateway;
import dev.omar.checkout.port.PaymentResult;
import dev.omar.checkout.port.PaymentUnavailableException;
import java.util.function.Supplier;

/**
 * STUB — returns one canned answer (or throws a canned failure) for every charge. Useful for
 * driving the SUT down a particular branch: approved, declined, provider down.
 */
public final class StubPaymentGateway implements PaymentGateway {

    private final Supplier<PaymentResult> answer;

    private StubPaymentGateway(Supplier<PaymentResult> answer) {
        this.answer = answer;
    }

    public static StubPaymentGateway approving(String transactionId) {
        return new StubPaymentGateway(() -> new PaymentResult.Approved(transactionId));
    }

    public static StubPaymentGateway declining(String reason) {
        return new StubPaymentGateway(() -> new PaymentResult.Declined(reason));
    }

    public static StubPaymentGateway unavailable(String message) {
        return new StubPaymentGateway(() -> {
            throw new PaymentUnavailableException(message);
        });
    }

    @Override
    public PaymentResult charge(ChargeRequest request) {
        return answer.get();
    }

    @Override
    public void refund(String transactionId) {
        // A stub has no opinion about commands; tests that care about refunds use a spy or mock.
    }
}
