package dev.omar.checkout.adapter;

import dev.omar.checkout.domain.Money;
import dev.omar.checkout.port.ChargeRequest;
import dev.omar.checkout.port.PaymentGateway;
import dev.omar.checkout.port.PaymentResult;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * A fake payment provider, in the spirit of a vendor "sandbox": it really keeps a ledger, honours
 * idempotency keys and declines charges above a per-charge limit, but no money moves.
 */
public final class SimulatedPaymentGateway implements PaymentGateway {

    private final Money perChargeLimit;
    private final Map<String, PaymentResult> resultsByKey = new HashMap<>();
    private final Map<String, Money> captured = new HashMap<>();
    private final Set<String> refunded = new HashSet<>();
    private int nextTransaction = 1;

    public SimulatedPaymentGateway(Money perChargeLimit) {
        this.perChargeLimit = Objects.requireNonNull(perChargeLimit, "perChargeLimit");
    }

    @Override
    public synchronized PaymentResult charge(ChargeRequest request) {
        // Replaying a key returns the original answer and never charges twice.
        return resultsByKey.computeIfAbsent(request.idempotencyKey(), key -> {
            if (request.amount().compareTo(perChargeLimit) > 0) {
                return new PaymentResult.Declined("amount " + request.amount() + " exceeds limit " + perChargeLimit);
            }
            String transactionId = "sim-tx-" + nextTransaction++;
            captured.put(transactionId, request.amount());
            return new PaymentResult.Approved(transactionId);
        });
    }

    @Override
    public synchronized void refund(String transactionId) {
        if (!captured.containsKey(transactionId)) {
            throw new IllegalArgumentException("unknown transaction: " + transactionId);
        }
        if (!refunded.add(transactionId)) {
            throw new IllegalStateException("already refunded: " + transactionId);
        }
    }

    /** Net money currently held: captured charges minus refunds. */
    public synchronized Money balance() {
        return captured.entrySet().stream()
                .filter(e -> !refunded.contains(e.getKey()))
                .map(Map.Entry::getValue)
                .reduce(Money.ZERO, Money::plus);
    }
}
