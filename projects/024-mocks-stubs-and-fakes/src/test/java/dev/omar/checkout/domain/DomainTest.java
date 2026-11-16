package dev.omar.checkout.domain;

import static dev.omar.checkout.Fixtures.ADA;
import static dev.omar.checkout.Fixtures.BOOK;
import static dev.omar.checkout.Fixtures.NOW;
import static dev.omar.checkout.Fixtures.cart;
import static dev.omar.checkout.Fixtures.item;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Value objects need no doubles at all — the cheapest tests in the suite. */
class DomainTest {

    @Test
    void moneyArithmeticAndFormatting() {
        assertEquals(Money.ofCents(3_05), Money.ofCents(1_00).plus(Money.ofCents(2_05)));
        assertEquals(Money.ofCents(7_50), Money.ofCents(2_50).times(3));
        assertEquals("$1234.05", Money.ofCents(1234_05).toString());
        assertThrows(IllegalArgumentException.class, () -> Money.ofCents(-1));
        assertThrows(ArithmeticException.class, () -> Money.ofCents(Long.MAX_VALUE).plus(Money.ofCents(1)));
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "book-1", "BOOK_1", "-BOOK", "BOOK--1", "BOOK 1"})
    void invalidSkusAreRejected(String code) {
        assertThrows(IllegalArgumentException.class, () -> new Sku(code));
    }

    @Test
    void requestRejectsDuplicateSkusAndNonPositiveQuantities() {
        assertThrows(IllegalArgumentException.class, () -> cart(ADA, item(BOOK, 1), item(BOOK, 2)));
        assertThrows(IllegalArgumentException.class, () -> item(BOOK, 0));
    }

    @Test
    void orderTotalIsTheSumOfItsLinesAndLinesAreImmutable() {
        Order order = new Order(new OrderId("o"), ADA,
                List.of(new OrderLine(BOOK, 2, Money.ofCents(3_00)), new OrderLine(new Sku("X1"), 1, Money.ofCents(50))),
                NOW, "tx");

        assertEquals(Money.ofCents(6_50), order.total());
        assertThrows(UnsupportedOperationException.class, () -> order.lines().clear());
        assertThrows(IllegalArgumentException.class, () -> new Order(new OrderId("o"), ADA, List.of(), NOW, "tx"));
    }
}
