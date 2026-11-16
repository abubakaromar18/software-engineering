package dev.omar.checkout.service;

import static dev.omar.checkout.Fixtures.ADA;
import static dev.omar.checkout.Fixtures.BOOK;
import static dev.omar.checkout.Fixtures.BOOK_PRICE;
import static dev.omar.checkout.Fixtures.MUG;
import static dev.omar.checkout.Fixtures.MUG_PRICE;
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
import dev.omar.checkout.domain.Order;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Spies: the interesting behaviour here is a side effect on a collaborator — stock being given
 * back when a later step fails. The result alone can't show that, so the spy records calls and
 * the test inspects them after the act step.
 */
@DisplayName("Test spies")
class CheckoutWithSpiesTest {

    private final StubCatalog catalog = new StubCatalog().price(BOOK, BOOK_PRICE).price(MUG, MUG_PRICE);
    private final SpyInventory inventory = new SpyInventory();

    @Test
    void stockAlreadyReservedIsReleasedWhenALaterLineIsOutOfStock() {
        inventory.outOfStock(MUG);
        CheckoutService service = checkout().catalog(catalog).inventory(inventory).build();

        service.placeOrder(cart(ADA, item(BOOK, 2), item(MUG, 1)));

        assertEquals(List.of("reserve BOOK-1 x2", "reserve MUG-2 x1", "release BOOK-1 x2"), inventory.calls());
    }

    @Test
    void allStockIsReleasedWhenPaymentIsDeclined() {
        CheckoutService service = checkout()
                .catalog(catalog).inventory(inventory)
                .payments(StubPaymentGateway.declining("card expired"))
                .build();

        service.placeOrder(cart(ADA, item(BOOK, 1), item(MUG, 3)));

        assertEquals(List.of("reserve BOOK-1 x1", "reserve MUG-2 x3", "release BOOK-1 x1", "release MUG-2 x3"),
                inventory.calls());
    }

    @Test
    void successfulCheckoutKeepsTheReservationAndSendsOneConfirmation() {
        SpyNotifier notifier = new SpyNotifier();
        CheckoutService service = checkout()
                .catalog(catalog).inventory(inventory)
                .payments(StubPaymentGateway.approving("tx-1"))
                .orders(new InMemoryOrderRepository())
                .notifier(notifier)
                .build();

        Order order = ((CheckoutResult.Placed) service.placeOrder(cart(ADA, item(BOOK, 1)))).order();

        assertEquals(List.of("reserve BOOK-1 x1"), inventory.calls());
        assertEquals(List.of(order), notifier.confirmed());
    }

    @Test
    void aFailingNotificationDoesNotFailAPaidOrder() {
        SpyNotifier notifier = new SpyNotifier().failingWith(new IllegalStateException("smtp down"));
        CheckoutService service = checkout()
                .catalog(catalog).inventory(inventory)
                .payments(StubPaymentGateway.approving("tx-1"))
                .orders(new InMemoryOrderRepository())
                .notifier(notifier)
                .build();

        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 1)));

        assertInstanceOf(CheckoutResult.Placed.class, result);
        assertEquals(1, notifier.confirmed().size(), "notification was attempted");
        assertEquals(List.of("reserve BOOK-1 x1"), inventory.calls(), "stock was not released");
    }
}
