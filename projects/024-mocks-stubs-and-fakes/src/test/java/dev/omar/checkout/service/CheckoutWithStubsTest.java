package dev.omar.checkout.service;

import static dev.omar.checkout.Fixtures.ADA;
import static dev.omar.checkout.Fixtures.BOOK;
import static dev.omar.checkout.Fixtures.BOOK_PRICE;
import static dev.omar.checkout.Fixtures.MUG;
import static dev.omar.checkout.Fixtures.MUG_PRICE;
import static dev.omar.checkout.Fixtures.NOW;
import static dev.omar.checkout.Fixtures.cart;
import static dev.omar.checkout.Fixtures.item;
import static dev.omar.checkout.service.CheckoutServiceBuilder.checkout;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import dev.omar.checkout.adapter.InMemoryOrderRepository;
import dev.omar.checkout.doubles.SpyInventory;
import dev.omar.checkout.doubles.SpyNotifier;
import dev.omar.checkout.doubles.StubCatalog;
import dev.omar.checkout.doubles.StubPaymentGateway;
import dev.omar.checkout.domain.CheckoutResult;
import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.OrderId;
import dev.omar.checkout.domain.OrderLine;
import dev.omar.checkout.domain.RejectionReason;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Stubs: feed the SUT canned answers to steer it down a branch, then check its <em>output</em>
 * (state verification). These tests say nothing about how the collaborators were called.
 */
@DisplayName("Stubs")
class CheckoutWithStubsTest {

    private final StubCatalog catalog = new StubCatalog().price(BOOK, BOOK_PRICE).price(MUG, MUG_PRICE);

    @Test
    void approvedPaymentProducesAPricedTimestampedOrder() {
        CheckoutService service = checkout()
                .catalog(catalog)
                .inventory(new SpyInventory())
                .payments(StubPaymentGateway.approving("tx-9"))
                .orders(new InMemoryOrderRepository())
                .notifier(new SpyNotifier())
                .build();

        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 2), item(MUG, 1)));

        Order order = assertInstanceOf(CheckoutResult.Placed.class, result).order();
        assertEquals(new OrderId("ORD-1"), order.id());
        assertEquals(List.of(new OrderLine(BOOK, 2, BOOK_PRICE), new OrderLine(MUG, 1, MUG_PRICE)), order.lines());
        assertEquals(Money.ofCents(47_50), order.total());
        assertEquals(NOW, order.placedAt());
        assertEquals("tx-9", order.paymentTransactionId());
    }

    @Test
    void declinedPaymentIsReportedWithTheProvidersReason() {
        CheckoutService service = checkout()
                .catalog(catalog)
                .inventory(new SpyInventory())
                .payments(StubPaymentGateway.declining("insufficient funds"))
                .build();

        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 1)));

        assertEquals(new CheckoutResult.Rejected(RejectionReason.PAYMENT_DECLINED, "insufficient funds"), result);
    }

    @Test
    void unreachableProviderIsAnExpectedRejectionNotACrash() {
        CheckoutService service = checkout()
                .catalog(catalog)
                .inventory(new SpyInventory())
                .payments(StubPaymentGateway.unavailable("timeout after 3s"))
                .build();

        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 1)));

        assertEquals(new CheckoutResult.Rejected(RejectionReason.PAYMENT_UNAVAILABLE, "timeout after 3s"), result);
    }

    @Test
    void outOfStockStopsTheCheckout() {
        CheckoutService service = checkout()
                .catalog(catalog)
                .inventory(new SpyInventory().outOfStock(MUG))
                .build(); // payments is still a dummy: proves we never got as far as charging

        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 1), item(MUG, 1)));

        assertEquals(new CheckoutResult.Rejected(RejectionReason.OUT_OF_STOCK, "MUG-2"), result);
    }
}
