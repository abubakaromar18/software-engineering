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
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

import dev.omar.checkout.adapter.InMemoryInventory;
import dev.omar.checkout.domain.CheckoutResult;
import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Order;
import dev.omar.checkout.domain.RejectionReason;
import dev.omar.checkout.port.Catalog;
import dev.omar.checkout.port.ChargeRequest;
import dev.omar.checkout.port.Inventory;
import dev.omar.checkout.port.Notifier;
import dev.omar.checkout.port.OrderRepository;
import dev.omar.checkout.port.PaymentGateway;
import dev.omar.checkout.port.PaymentResult;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;

/**
 * The same scenarios, written with Mockito. One library object plays every role: it is a stub
 * when you {@code when(...).thenReturn(...)}, a mock when you {@code verify(...)}, and
 * {@code spy(realObject)} gives a partial mock over a fake. Less code to write, but the role
 * each double plays is now implicit — the hand-rolled tests make it explicit.
 */
@DisplayName("Mockito")
class CheckoutWithMockitoTest {

    private Catalog catalog;
    private Inventory inventory;
    private PaymentGateway payments;
    private OrderRepository orders;
    private Notifier notifier;

    @BeforeEach
    void createMocks() {
        catalog = mock(Catalog.class);
        inventory = mock(Inventory.class);
        payments = mock(PaymentGateway.class);
        orders = mock(OrderRepository.class);
        notifier = mock(Notifier.class);
        // Stubbing: Mockito's defaults (false, null) are rarely what a happy path needs.
        when(catalog.priceOf(BOOK)).thenReturn(Optional.of(BOOK_PRICE));
        when(catalog.priceOf(MUG)).thenReturn(Optional.of(MUG_PRICE));
        when(inventory.reserve(any(), anyInt())).thenReturn(true);
    }

    private CheckoutService service() {
        return checkout().catalog(catalog).inventory(inventory).payments(payments)
                .orders(orders).notifier(notifier).build();
    }

    @Test
    void asAStub_unknownSkuGivesUnknownItem() {
        when(catalog.priceOf(MUG)).thenReturn(Optional.empty());

        CheckoutResult result = service().placeOrder(cart(ADA, item(MUG, 1)));

        assertEquals(new CheckoutResult.Rejected(RejectionReason.UNKNOWN_ITEM, "MUG-2"), result);
        verify(inventory, never()).reserve(any(), anyInt());
    }

    @Test
    void asAMock_chargeIsMadeWithTheExactRequest() {
        when(payments.charge(any())).thenReturn(new PaymentResult.Approved("tx-1"));

        service().placeOrder(cart(ADA, item(BOOK, 1), item(MUG, 2)));

        verify(payments).charge(new ChargeRequest(ADA, Money.ofCents(35_00), "ORD-1"));
        verifyNoMoreInteractions(payments); // no refund on the happy path
    }

    @Test
    void withAnArgumentCaptor_theSavedOrderIsTheOneThatIsConfirmed() {
        when(payments.charge(any())).thenReturn(new PaymentResult.Approved("tx-5"));
        ArgumentCaptor<Order> saved = ArgumentCaptor.forClass(Order.class);

        service().placeOrder(cart(ADA, item(BOOK, 1)));

        verify(orders).save(saved.capture());
        assertEquals("tx-5", saved.getValue().paymentTransactionId());
        verify(notifier).orderConfirmed(saved.getValue());
    }

    @Test
    void withInOrder_compensationsRunInTheRightSequence() {
        when(payments.charge(any())).thenReturn(new PaymentResult.Approved("tx-2"));
        doThrow(new IllegalStateException("disk full")).when(orders).save(any());

        assertThrows(CheckoutFailedException.class, () -> service().placeOrder(cart(ADA, item(BOOK, 1))));

        InOrder sequence = inOrder(inventory, payments, orders);
        sequence.verify(inventory).reserve(BOOK, 1);
        sequence.verify(payments).charge(any());
        sequence.verify(orders).save(any());
        sequence.verify(payments).refund("tx-2");
        sequence.verify(inventory).release(BOOK, 1);
        verify(notifier, never()).orderConfirmed(any());
    }

    @Test
    void asASpyOverAFake_realBehaviourWithOneOverriddenMethod() {
        InMemoryInventory realStock = new InMemoryInventory(Map.of(BOOK, 5, MUG, 5));
        Inventory spied = spy(realStock);
        doReturn(false).when(spied).reserve(MUG, 1); // simulate a race: someone took the last mug
        when(payments.charge(any())).thenReturn(new PaymentResult.Approved("tx-3"));
        CheckoutService service = checkout().catalog(catalog).inventory(spied).payments(payments).build();

        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 2), item(MUG, 1)));

        assertInstanceOf(CheckoutResult.Rejected.class, result);
        verify(spied).release(BOOK, 2);
        // The spy delegated to the real object: the stock round-tripped back to five.
        assertEquals(5, ((InMemoryInventory) spied).available(BOOK));
    }
}
