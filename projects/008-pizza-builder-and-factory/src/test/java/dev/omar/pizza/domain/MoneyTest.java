package dev.omar.pizza.domain;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class MoneyTest {

    @Test
    void parsesAndPrintsDollars() {
        assertEquals(1250, Money.of("12.50").cents());
        assertEquals("$12.50", Money.of("12.5").toString());
        assertEquals("$0.07", Money.ofCents(7).toString());
    }

    @Test
    void rejectsFractionsOfACentAndNegatives() {
        assertThrows(IllegalArgumentException.class, () -> Money.of("1.005"));
        assertThrows(IllegalArgumentException.class, () -> Money.ofCents(-1));
    }

    @Test
    void decimalMultiplicationUsesBankersRounding() {
        // 0.5 cent ties go to the even neighbour: 2.5 -> 2, 3.5 -> 4
        assertEquals(2, Money.ofCents(5).times(new BigDecimal("0.5")).cents());
        assertEquals(4, Money.ofCents(7).times(new BigDecimal("0.5")).cents());
    }

    @Test
    void addsAndMultipliesByQuantity() {
        assertEquals(Money.of("7.50"), Money.of("2.50").times(2).plus(Money.of("2.50")));
    }
}
