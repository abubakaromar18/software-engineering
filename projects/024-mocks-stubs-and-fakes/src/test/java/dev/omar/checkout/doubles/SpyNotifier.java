package dev.omar.checkout.doubles;

import dev.omar.checkout.domain.Order;
import dev.omar.checkout.port.Notifier;
import java.util.ArrayList;
import java.util.List;

/** SPY — records each confirmation; can also be told to fail, to test that failures are tolerated. */
public final class SpyNotifier implements Notifier {

    private final List<Order> confirmed = new ArrayList<>();
    private RuntimeException failure;

    public SpyNotifier failingWith(RuntimeException failure) {
        this.failure = failure;
        return this;
    }

    @Override
    public void orderConfirmed(Order order) {
        confirmed.add(order);
        if (failure != null) {
            throw failure;
        }
    }

    public List<Order> confirmed() {
        return List.copyOf(confirmed);
    }
}
