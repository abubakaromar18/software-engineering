package dev.omar.checkout.service;

import dev.omar.checkout.domain.CheckoutRequest;
import dev.omar.checkout.domain.CheckoutResult;
import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.domain.OrderLine;
import dev.omar.checkout.domain.RejectionReason;
import dev.omar.checkout.port.Catalog;
import dev.omar.checkout.port.ChargeRequest;
import dev.omar.checkout.port.Inventory;
import dev.omar.checkout.port.Notifier;
import dev.omar.checkout.port.OrderIdGenerator;
import dev.omar.checkout.port.OrderRepository;
import dev.omar.checkout.port.PaymentGateway;
import dev.omar.checkout.port.PaymentResult;
import dev.omar.checkout.port.PaymentUnavailableException;
import java.time.Clock;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * Places orders. This is the single "system under test" that every test-double style in the test
 * suite exercises. Each collaborator is an interface injected through the constructor, which is
 * what makes substituting doubles possible in the first place.
 *
 * <p>Workflow: price → reserve stock → charge → persist → notify. Each step that fails undoes
 * the earlier ones (a small saga with compensating actions), and those compensations are exactly
 * the kind of behaviour that only spies and mocks can observe.
 */
public final class CheckoutService {

    private static final System.Logger LOG = System.getLogger(CheckoutService.class.getName());

    private final Catalog catalog;
    private final Inventory inventory;
    private final PaymentGateway payments;
    private final OrderRepository orders;
    private final Notifier notifier;
    private final OrderIdGenerator ids;
    private final Clock clock;

    public CheckoutService(Catalog catalog, Inventory inventory, PaymentGateway payments,
                           OrderRepository orders, Notifier notifier, OrderIdGenerator ids, Clock clock) {
        this.catalog = Objects.requireNonNull(catalog, "catalog");
        this.inventory = Objects.requireNonNull(inventory, "inventory");
        this.payments = Objects.requireNonNull(payments, "payments");
        this.orders = Objects.requireNonNull(orders, "orders");
        this.notifier = Objects.requireNonNull(notifier, "notifier");
        this.ids = Objects.requireNonNull(ids, "ids");
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    /**
     * Attempts to place an order.
     *
     * @return {@link CheckoutResult.Placed} on success, {@link CheckoutResult.Rejected} for expected
     *     business failures (nothing is left reserved or charged)
     * @throws CheckoutFailedException if the order could not be stored after payment; the payment is
     *     refunded and stock released before this is thrown
     */
    public CheckoutResult placeOrder(CheckoutRequest request) {
        Objects.requireNonNull(request, "request");
        if (request.items().isEmpty()) {
            return reject(RejectionReason.EMPTY_CART, "cart has no items");
        }

        List<OrderLine> lines = new ArrayList<>();
        for (CheckoutRequest.Item item : request.items()) {
            Optional<Money> price = catalog.priceOf(item.sku());
            if (price.isEmpty()) {
                return reject(RejectionReason.UNKNOWN_ITEM, item.sku().code());
            }
            lines.add(new OrderLine(item.sku(), item.quantity(), price.get()));
        }

        List<OrderLine> reserved = new ArrayList<>();
        for (OrderLine line : lines) {
            if (!inventory.reserve(line.sku(), line.quantity())) {
                release(reserved);
                return reject(RejectionReason.OUT_OF_STOCK, line.sku().code());
            }
            reserved.add(line);
        }

        OrderId id = ids.next();
        Money total = lines.stream().map(OrderLine::lineTotal).reduce(Money.ZERO, Money::plus);
        PaymentResult payment;
        try {
            payment = payments.charge(new ChargeRequest(request.customer(), total, id.value()));
        } catch (PaymentUnavailableException e) {
            release(reserved);
            return reject(RejectionReason.PAYMENT_UNAVAILABLE, e.getMessage());
        }

        return switch (payment) {
            case PaymentResult.Declined declined -> {
                release(reserved);
                yield reject(RejectionReason.PAYMENT_DECLINED, declined.reason());
            }
            case PaymentResult.Approved approved -> {
                Order order = new Order(id, request.customer(), lines, clock.instant(), approved.transactionId());
                persist(order, reserved);
                notifyCustomer(order);
                yield new CheckoutResult.Placed(order);
            }
        };
    }

    /** A customer's orders, newest first. */
    public List<Order> orderHistory(CustomerId customer) {
        return orders.findByCustomer(customer).stream()
                .sorted(Comparator.comparing(Order::placedAt).reversed())
                .toList();
    }

    private void persist(Order order, List<OrderLine> reserved) {
        try {
            orders.save(order);
        } catch (RuntimeException e) {
            // Money has been taken but there is no order: undo both, then surface the failure.
            payments.refund(order.paymentTransactionId());
            release(reserved);
            throw new CheckoutFailedException("could not store order " + order.id(), e);
        }
    }

    private void notifyCustomer(Order order) {
        try {
            notifier.orderConfirmed(order);
        } catch (RuntimeException e) {
            // The order is real and paid for; a lost email must not turn it into a failure.
            LOG.log(System.Logger.Level.WARNING, "confirmation for order " + order.id() + " not sent", e);
        }
    }

    private void release(List<OrderLine> reserved) {
        for (OrderLine line : reserved) {
            inventory.release(line.sku(), line.quantity());
        }
    }

    private static CheckoutResult reject(RejectionReason reason, String detail) {
        return new CheckoutResult.Rejected(reason, detail);
    }
}
