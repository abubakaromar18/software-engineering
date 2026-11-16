package dev.omar.checkout.doubles;

import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.port.OrderRepository;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;
import java.util.Optional;

/** STUB (saboteur variant) — simulates the database being down so error paths can be tested. */
public final class FailingOrderRepository implements OrderRepository {

    @Override
    public void save(Order order) {
        throw new UncheckedIOException(new IOException("database unavailable"));
    }

    @Override
    public Optional<Order> findById(OrderId id) {
        throw new UncheckedIOException(new IOException("database unavailable"));
    }

    @Override
    public List<Order> findByCustomer(CustomerId customer) {
        throw new UncheckedIOException(new IOException("database unavailable"));
    }
}
