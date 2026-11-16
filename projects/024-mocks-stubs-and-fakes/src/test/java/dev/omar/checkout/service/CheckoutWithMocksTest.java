package dev.omar.checkout.service;

import static dev.omar.checkout.Fixtures.ADA;
import static dev.omar.checkout.Fixtures.BOOK;
import static dev.omar.checkout.Fixtures.BOOK_PRICE;
import static dev.omar.checkout.Fixtures.cart;
import static dev.omar.checkout.Fixtures.item;
import static dev.omar.checkout.service.CheckoutServiceBuilder.checkout;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

import dev.omar.checkout.adapter.InMemoryOrderRepository;
import dev.omar.checkout.doubles.FailingOrderRepository;
import dev.omar.checkout.doubles.MockPaymentGateway;
import dev.omar.checkout.doubles.SpyInventory;
import dev.omar.checkout.doubles.SpyNotifier;
import dev.omar.checkout.doubles.StubCatalog;
import dev.omar.checkout.domain.CheckoutResult;
import dev.omar.checkout.domain.Money;
import dev.omar.checkout.port.ChargeRequest;
import dev.omar.checkout.port.PaymentResult;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Mocks: the payment conversation is the contract that matters — the exact amount, the
 * idempotency key, and a refund if we can't keep our side of the bargain. Expectations are
 * written first; the mock fails on any deviation.
 */
@DisplayName("Mock objects")
class CheckoutWithMocksTest {

    private final StubCatalog catalog = new StubCatalog().price(BOOK, BOOK_PRICE);
    private final SpyInventory inventory = new SpyInventory();

    @Test
    void chargesTheOrderTotalOnceUsingTheOrderIdAsIdempotencyKey() {
        MockPaymentGateway payments = new MockPaymentGateway()
                .expectCharge(new ChargeRequest(ADA, Money.ofCents(60_00), "ORD-1"), new PaymentResult.Approved("tx-1"));
        CheckoutService service = checkout()
                .catalog(catalog).inventory(inventory).payments(payments)
                .orders(new InMemoryOrderRepository()).notifier(new SpyNotifier())
                .build();

        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 3)));

        assertInstanceOf(CheckoutResult.Placed.class, result);
        payments.verify();
    }

    @Test
    void refundsThePaymentWhenTheOrderCannotBeStored() {
        MockPaymentGateway payments = new MockPaymentGateway()
                .expectCharge(new ChargeRequest(ADA, BOOK_PRICE, "ORD-1"), new PaymentResult.Approved("tx-77"))
                .expectRefund("tx-77");
        CheckoutService service = checkout()
                .catalog(catalog).inventory(inventory).payments(payments)
                .orders(new FailingOrderRepository())
                .build(); // notifier stays a dummy: no confirmation for an order that doesn't exist

        CheckoutFailedException failure = assertThrows(CheckoutFailedException.class,
                () -> service.placeOrder(cart(ADA, item(BOOK, 1))));

        payments.verify();
        assertEquals("could not store order ORD-1", failure.getMessage());
        assertEquals(List.of("reserve BOOK-1 x1", "release BOOK-1 x1"), inventory.calls());
    }

    @Test
    void aMockRejectsAConversationItWasNotProgrammedFor() {
        MockPaymentGateway payments = new MockPaymentGateway()
                .expectCharge(new ChargeRequest(ADA, Money.ofCents(1), "ORD-1"), new PaymentResult.Approved("tx-1"));
        CheckoutService service = checkout().catalog(catalog).inventory(inventory).payments(payments).build();

        AssertionError error = assertThrows(AssertionError.class, () -> service.placeOrder(cart(ADA, item(BOOK, 1))));

        assertEquals("charge called with ChargeRequest[customer=ada, amount=$20.00, idempotencyKey=ORD-1]"
                + " but expected ChargeRequest[customer=ada, amount=$0.01, idempotencyKey=ORD-1]", error.getMessage());
    }

    @Test
    void verifyReportsExpectationsThatWereNeverMet() {
        MockPaymentGateway payments = new MockPaymentGateway().expectRefund("tx-1");

        AssertionError error = assertThrows(AssertionError.class, payments::verify);

        assertEquals("expected calls never made: [ExpectRefund[transactionId=tx-1]]", error.getMessage());
    }
}
