package dev.omar.checkout.port;

import dev.omar.checkout.domain.Order;

/** Tells the customer about their order (email, SMS…). Best-effort from the service's point of view. */
public interface Notifier {

    void orderConfirmed(Order order);
}
