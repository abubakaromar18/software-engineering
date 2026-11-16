package dev.omar.checkout.adapter;

import dev.omar.checkout.domain.Sku;
import dev.omar.checkout.port.Inventory;
import java.util.HashMap;
import java.util.Map;

/**
 * Thread-safe in-memory stock levels. A <em>fake</em> in the test-double sense: a real, working
 * implementation that takes a shortcut (no warehouse system), cheap enough to use in tests.
 * Deliberately not final so Mockito can wrap it in a partial-mock spy.
 */
public class InMemoryInventory implements Inventory {

    private final Map<Sku, Integer> stock = new HashMap<>();

    public InMemoryInventory(Map<Sku, Integer> initialStock) {
        initialStock.forEach((sku, quantity) -> {
            if (quantity < 0) {
                throw new IllegalArgumentException("negative stock for " + sku);
            }
            stock.put(sku, quantity);
        });
    }

    @Override
    public synchronized boolean reserve(Sku sku, int quantity) {
        requirePositive(quantity);
        int available = stock.getOrDefault(sku, 0);
        if (available < quantity) {
            return false;
        }
        stock.put(sku, available - quantity);
        return true;
    }

    @Override
    public synchronized void release(Sku sku, int quantity) {
        requirePositive(quantity);
        stock.merge(sku, quantity, Integer::sum);
    }

    public synchronized int available(Sku sku) {
        return stock.getOrDefault(sku, 0);
    }

    private static void requirePositive(int quantity) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be positive: " + quantity);
        }
    }
}
