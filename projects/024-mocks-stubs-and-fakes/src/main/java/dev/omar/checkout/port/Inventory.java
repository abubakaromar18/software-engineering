package dev.omar.checkout.port;

import dev.omar.checkout.domain.Sku;

/** Stock reservations. A command port: tests care about which calls were made (spies, mocks). */
public interface Inventory {

    /** Reserves {@code quantity} units; returns {@code false} (and reserves nothing) if not enough stock. */
    boolean reserve(Sku sku, int quantity);

    /** Returns previously reserved units to stock. */
    void release(Sku sku, int quantity);
}
