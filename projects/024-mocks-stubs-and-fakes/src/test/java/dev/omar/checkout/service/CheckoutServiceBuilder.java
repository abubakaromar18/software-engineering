package dev.omar.checkout.service;

import dev.omar.checkout.Fixtures;
import dev.omar.checkout.doubles.Dummy;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.port.Catalog;
import dev.omar.checkout.port.Inventory;
import dev.omar.checkout.port.Notifier;
import dev.omar.checkout.port.OrderIdGenerator;
import dev.omar.checkout.port.OrderRepository;
import dev.omar.checkout.port.PaymentGateway;
import java.time.Clock;

/**
 * Test Data Builder for the SUT. Every collaborator defaults to a {@link Dummy}, so a test only
 * names the doubles that matter to it — and if the code under test touches anything else, the
 * dummy fails the test. Ids default to a stub returning {@code ORD-1}, the clock to a fixed one.
 */
public final class CheckoutServiceBuilder {

    private Catalog catalog = Dummy.of(Catalog.class);
    private Inventory inventory = Dummy.of(Inventory.class);
    private PaymentGateway payments = Dummy.of(PaymentGateway.class);
    private OrderRepository orders = Dummy.of(OrderRepository.class);
    private Notifier notifier = Dummy.of(Notifier.class);
    private OrderIdGenerator ids = () -> new OrderId("ORD-1");
    private Clock clock = Fixtures.FIXED_CLOCK;

    public static CheckoutServiceBuilder checkout() {
        return new CheckoutServiceBuilder();
    }

    public CheckoutServiceBuilder catalog(Catalog value) {
        catalog = value;
        return this;
    }

    public CheckoutServiceBuilder inventory(Inventory value) {
        inventory = value;
        return this;
    }

    public CheckoutServiceBuilder payments(PaymentGateway value) {
        payments = value;
        return this;
    }

    public CheckoutServiceBuilder orders(OrderRepository value) {
        orders = value;
        return this;
    }

    public CheckoutServiceBuilder notifier(Notifier value) {
        notifier = value;
        return this;
    }

    public CheckoutServiceBuilder ids(OrderIdGenerator value) {
        ids = value;
        return this;
    }

    public CheckoutServiceBuilder clock(Clock value) {
        clock = value;
        return this;
    }

    public CheckoutService build() {
        return new CheckoutService(catalog, inventory, payments, orders, notifier, ids, clock);
    }
}
