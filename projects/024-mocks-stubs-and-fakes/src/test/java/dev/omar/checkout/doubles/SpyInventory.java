package dev.omar.checkout.doubles;

import dev.omar.checkout.domain.Sku;
import dev.omar.checkout.port.Inventory;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * SPY — a stub that also records how it was called, so the test can inspect the interaction
 * <em>afterwards</em> (arrange–act–assert). Contrast with {@link MockPaymentGateway}, where the
 * expectations are declared up front.
 */
public final class SpyInventory implements Inventory {

    private final Set<Sku> outOfStock = new HashSet<>();
    private final List<String> calls = new ArrayList<>();

    public SpyInventory outOfStock(Sku sku) {
        outOfStock.add(sku);
        return this;
    }

    @Override
    public boolean reserve(Sku sku, int quantity) {
        calls.add("reserve " + sku + " x" + quantity);
        return !outOfStock.contains(sku);
    }

    @Override
    public void release(Sku sku, int quantity) {
        calls.add("release " + sku + " x" + quantity);
    }

    /** Every call in order, e.g. {@code ["reserve BOOK-1 x2", "release BOOK-1 x2"]}. */
    public List<String> calls() {
        return List.copyOf(calls);
    }
}
