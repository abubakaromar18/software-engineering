package dev.omar.checkout.service;

import static dev.omar.checkout.Fixtures.ADA;
import static dev.omar.checkout.Fixtures.BOOK;
import static dev.omar.checkout.Fixtures.cart;
import static dev.omar.checkout.Fixtures.item;
import static dev.omar.checkout.service.CheckoutServiceBuilder.checkout;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import dev.omar.checkout.doubles.Dummy;
import dev.omar.checkout.doubles.StubCatalog;
import dev.omar.checkout.domain.CheckoutResult;
import dev.omar.checkout.domain.RejectionReason;
import dev.omar.checkout.port.Inventory;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Dummies: the early-exit paths need a fully constructed service, but none of its downstream
 * collaborators. Because every default in the builder is a strict dummy, these tests also prove
 * that no stock is reserved and no money is charged on those paths.
 */
@DisplayName("Dummy objects")
class CheckoutWithDummiesTest {

    @Test
    void emptyCartIsRejectedWithoutTouchingAnyCollaborator() {
        CheckoutService service = checkout().build(); // every collaborator is a dummy

        CheckoutResult result = service.placeOrder(cart(ADA));

        assertEquals(new CheckoutResult.Rejected(RejectionReason.EMPTY_CART, "cart has no items"), result);
    }

    @Test
    void unknownItemIsRejectedBeforeInventoryOrPaymentAreUsed() {
        CheckoutService service = checkout().catalog(new StubCatalog()).build(); // empty catalog

        CheckoutResult result = service.placeOrder(cart(ADA, item(BOOK, 1)));

        assertEquals(new CheckoutResult.Rejected(RejectionReason.UNKNOWN_ITEM, "BOOK-1"), result);
    }

    @Test
    void aDummyFailsTheTestIfTheCodeUnexpectedlyUsesIt() {
        Inventory dummy = Dummy.of(Inventory.class);

        AssertionError error = assertThrows(AssertionError.class, () -> dummy.reserve(BOOK, 1));

        assertEquals("dummy Inventory.reserve() must not be called", error.getMessage());
    }
}
