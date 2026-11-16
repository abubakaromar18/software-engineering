package dev.omar.checkout.port;

import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.OrderId;
import java.util.List;
import java.util.Optional;

/**
 * Persistence for placed orders. Every implementation — including the in-memory fake — must pass
 * {@code OrderRepositoryContract}, which is what makes the fake trustworthy.
 */
public interface OrderRepository {

    /**
     * Stores a new order.
     *
     * @throws DuplicateOrderException if an order with the same id already exists (orders are immutable)
     */
    void save(Order order);

    Optional<Order> findById(OrderId id);

    /** All orders for a customer, in the order they were saved. */
    List<Order> findByCustomer(CustomerId customer);
}
