package dev.omar.checkout.adapter;

import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.port.OrderIdGenerator;
import java.util.concurrent.atomic.AtomicLong;

/** Generates {@code PREFIX-1}, {@code PREFIX-2}, … — readable ids for the demo and tests. */
public final class SequentialOrderIdGenerator implements OrderIdGenerator {

    private final String prefix;
    private final AtomicLong counter = new AtomicLong();

    public SequentialOrderIdGenerator(String prefix) {
        if (prefix == null || prefix.isBlank()) {
            throw new IllegalArgumentException("prefix must not be blank");
        }
        this.prefix = prefix;
    }

    @Override
    public OrderId next() {
        return new OrderId(prefix + "-" + counter.incrementAndGet());
    }
}
