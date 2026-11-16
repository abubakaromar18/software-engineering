package dev.omar.checkout.service;

import static dev.omar.checkout.Fixtures.ADA;
import static dev.omar.checkout.Fixtures.BOOK;
import static dev.omar.checkout.Fixtures.BOOK_PRICE;
import static dev.omar.checkout.Fixtures.GRACE;
import static dev.omar.checkout.Fixtures.MUG;
import static dev.omar.checkout.Fixtures.MUG_PRICE;
import static dev.omar.checkout.Fixtures.cart;
import static dev.omar.checkout.Fixtures.item;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import dev.omar.checkout.adapter.InMemoryCatalog;
import dev.omar.checkout.adapter.InMemoryInventory;
import dev.omar.checkout.adapter.InMemoryOrderRepository;
import dev.omar.checkout.adapter.SequentialOrderIdGenerator;
import dev.omar.checkout.adapter.SimulatedPaymentGateway;
import dev.omar.checkout.doubles.SpyNotifier;
import dev.omar.checkout.domain.CheckoutResult;
import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.domain.RejectionReason;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Fakes: working implementations with shortcuts. Tests read like scenarios over real state —
 * stock levels, a ledger, stored orders — and survive refactoring of <em>how</em> the service
 * talks to its collaborators, because they only look at outcomes.
 */
@DisplayName("Fake objects")
class CheckoutWithFakesTest {

    private InMemoryInventory inventory;
    private SimulatedPaymentGateway payments;
    private InMemoryOrderRepository orders;
    private MutableClock clock;
    private CheckoutService service;

    @BeforeEach
    void wireFakes() {
        inventory = new InMemoryInventory(Map.of(BOOK, 10, MUG, 2));
        payments = new SimulatedPaymentGateway(Money.ofCents(100_00));
        orders = new InMemoryOrderRepository();
        clock = new MutableClock(Instant.parse("2026-11-16T09:00:00Z"));
        service = new CheckoutService(new InMemoryCatalog(Map.of(BOOK, BOOK_PRICE, MUG, MUG_PRICE)),
                inventory, payments, orders, new SpyNotifier(), new SequentialOrderIdGenerator("ORD"), clock);
    }

    @Test
    void aPlacedOrderIsStoredStockIsDeductedAndMoneyIsCaptured() {
        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 2), item(MUG, 1)));

        OrderId id = assertInstanceOf(CheckoutResult.Placed.class, result).order().id();
        assertEquals(id, orders.findById(id).orElseThrow().id());
        assertEquals(8, inventory.available(BOOK));
        assertEquals(1, inventory.available(MUG));
        assertEquals(Money.ofCents(47_50), payments.balance());
    }

    @Test
    void aDeclinedOrderLeavesNoTrace() {
        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 6))); // $120 > $100 limit

        assertEquals(RejectionReason.PAYMENT_DECLINED, ((CheckoutResult.Rejected) result).reason());
        assertEquals(10, inventory.available(BOOK));
        assertEquals(Money.ZERO, payments.balance());
        assertEquals(List.of(), orders.findByCustomer(ADA));
    }

    @Test
    void stockRunsOutAcrossSuccessiveCheckouts() {
        service.placeOrder(cart(ADA, item(MUG, 2)));

        CheckoutResult second = service.placeOrder(cart(GRACE, item(MUG, 1)));

        assertEquals(new CheckoutResult.Rejected(RejectionReason.OUT_OF_STOCK, "MUG-2"), second);
    }

    @Test
    void orderHistoryIsPerCustomerAndNewestFirst() {
        service.placeOrder(cart(ADA, item(BOOK, 1)));
        clock.advance(Duration.ofHours(1));
        service.placeOrder(cart(GRACE, item(BOOK, 1)));
        clock.advance(Duration.ofHours(1));
        service.placeOrder(cart(ADA, item(MUG, 1)));

        List<String> adaOrders = service.orderHistory(ADA).stream().map(o -> o.id().value()).toList();

        assertEquals(List.of("ORD-3", "ORD-1"), adaOrders);
    }

    /** A controllable clock: a tiny fake of time itself. */
    private static final class MutableClock extends Clock {
        private Instant now;

        MutableClock(Instant start) {
            now = start;
        }

        void advance(Duration duration) {
            now = now.plus(duration);
        }

        @Override
        public ZoneOffset getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            throw new UnsupportedOperationException("fixed to UTC");
        }

        @Override
        public Instant instant() {
            return now;
        }
    }
}
