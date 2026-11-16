package dev.omar.checkout.domain;

import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * What the customer asked to buy. Structural rules (positive quantities, no duplicate SKUs) are
 * enforced here; business rules (empty cart, unknown items, stock) belong to the service.
 */
public record CheckoutRequest(CustomerId customer, List<Item> items) {

    /** A requested SKU and quantity, before pricing. */
    public record Item(Sku sku, int quantity) {
        public Item {
            Objects.requireNonNull(sku, "sku");
            if (quantity <= 0) {
                throw new IllegalArgumentException("quantity must be positive: " + quantity);
            }
        }
    }

    public CheckoutRequest {
        Objects.requireNonNull(customer, "customer");
        items = List.copyOf(items);
        Set<Sku> seen = new HashSet<>();
        for (Item item : items) {
            if (!seen.add(item.sku())) {
                throw new IllegalArgumentException("duplicate SKU in request: " + item.sku());
            }
        }
    }
}
