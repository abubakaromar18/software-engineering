package dev.omar.checkout.adapter;

import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.port.DuplicateOrderException;
import dev.omar.checkout.port.OrderRepository;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * The canonical <em>fake</em>: a complete repository backed by a map. It lives in main (not test)
 * so the demo, local development and other modules' tests can all use the same verified fake.
 */
public final class InMemoryOrderRepository implements OrderRepository {

    private final Map<OrderId, Order> byId = new LinkedHashMap<>();

    @Override
    public synchronized void save(Order order) {
        if (byId.putIfAbsent(order.id(), order) != null) {
            throw new DuplicateOrderException(order.id());
        }
    }

    @Override
    public synchronized Optional<Order> findById(OrderId id) {
        return Optional.ofNullable(byId.get(id));
    }

    @Override
    public synchronized List<Order> findByCustomer(CustomerId customer) {
        return byId.values().stream().filter(o -> o.customer().equals(customer)).toList();
    }
}
