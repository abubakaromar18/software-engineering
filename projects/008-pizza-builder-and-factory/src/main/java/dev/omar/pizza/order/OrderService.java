package dev.omar.pizza.order;

import dev.omar.pizza.store.PizzaStore;

import java.math.BigDecimal;
import java.util.List;
import java.util.Objects;

/**
 * Turns customer requests into an {@link Order}. It knows only the abstract {@link PizzaStore},
 * so it works unchanged with any region, including stores that do not exist yet.
 */
public final class OrderService {

    private final PizzaStore store;
    private final BigDecimal taxRate;

    public OrderService(PizzaStore store, BigDecimal taxRate) {
        this.store = Objects.requireNonNull(store, "store");
        this.taxRate = Objects.requireNonNull(taxRate, "taxRate");
    }

    /**
     * Places the whole order or nothing: if any request is rejected the exception propagates and
     * no partial order is returned.
     */
    public Order place(List<PizzaRequest> requests) {
        List<OrderLine> lines = requests.stream()
                .map(r -> new OrderLine(store.orderPizza(r.item(), r.size(), r.extras()), r.quantity()))
                .toList();
        return new Order(store.name(), lines, taxRate);
    }
}
