package dev.omar.checkout.port;

import dev.omar.checkout.domain.OrderId;

/** Source of fresh order ids. Injected so tests get predictable ids. */
@FunctionalInterface
public interface OrderIdGenerator {

    OrderId next();
}
