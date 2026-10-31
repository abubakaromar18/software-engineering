package dev.omar.pizza.order;

import dev.omar.pizza.domain.Money;
import dev.omar.pizza.domain.Size;
import dev.omar.pizza.domain.Topping;
import dev.omar.pizza.store.ChicagoPizzaStore;
import dev.omar.pizza.store.MenuItem;
import dev.omar.pizza.store.NewYorkPizzaStore;
import dev.omar.pizza.store.UnsupportedOrderException;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class OrderTest {

    private static final BigDecimal TAX = new BigDecimal("0.0825");

    @Nested
    class Totals {

        @Test
        void computesSubtotalTaxAndTotal() {
            Order order = new OrderService(new NewYorkPizzaStore(), TAX).place(List.of(
                    new PizzaRequest(MenuItem.PEPPERONI, Size.LARGE, List.of(Topping.MUSHROOM), 2),
                    new PizzaRequest(MenuItem.MARGHERITA, Size.SMALL, List.of(), 1)));

            assertEquals(Money.of("36.00"), order.subtotal()); // 2 * 14.25 + 7.50
            assertEquals(Money.of("2.97"), order.tax());
            assertEquals(Money.of("38.97"), order.total());
            assertEquals(3, order.pizzaCount());
        }

        @Test
        void receiptListsLinesAndTotals() {
            Order order = new OrderService(new NewYorkPizzaStore(), TAX)
                    .place(List.of(PizzaRequest.parse("veggie/m")));
            String receipt = order.receipt();
            assertTrue(receipt.startsWith("Brooklyn Slice Co. (New York)\n"), receipt);
            assertTrue(receipt.contains("New York Style Garden Veggie (Medium)"), receipt);
            assertTrue(receipt.contains("vegetarian"), receipt);
            assertTrue(receipt.contains("Tax (8.25%)"), receipt);
            assertTrue(receipt.contains("Total (1 pizza)"), receipt);
        }

        @Test
        void rejectsEmptyOrdersAndBadTaxRates() {
            assertThrows(IllegalArgumentException.class, () -> new Order("x", List.of(), TAX));
            var line = new OrderLine(new NewYorkPizzaStore().orderPizza(MenuItem.CHEESE, Size.SMALL), 1);
            assertThrows(IllegalArgumentException.class, () -> new Order("x", List.of(line), BigDecimal.ONE));
            assertThrows(IllegalArgumentException.class, () -> new Order("x", List.of(line), new BigDecimal("-0.01")));
        }

        @ParameterizedTest
        @ValueSource(ints = {0, 21})
        void rejectsQuantitiesOutOfRange(int quantity) {
            var pizza = new NewYorkPizzaStore().orderPizza(MenuItem.CHEESE, Size.SMALL);
            assertThrows(IllegalArgumentException.class, () -> new OrderLine(pizza, quantity));
        }

        @Test
        void placingIsAllOrNothing() {
            OrderService service = new OrderService(new ChicagoPizzaStore(), TAX);
            assertThrows(UnsupportedOrderException.class, () -> service.place(List.of(
                    PizzaRequest.parse("cheese/large"),
                    PizzaRequest.parse("cheese/small"))));
        }
    }

    @Nested
    class Parsing {

        @Test
        void parsesTheFullSyntax() {
            PizzaRequest r = PizzaRequest.parse("3:meat-lovers/L/+green-pepper+Onion");
            assertEquals(new PizzaRequest(MenuItem.MEAT_LOVERS, Size.LARGE,
                    List.of(Topping.GREEN_PEPPER, Topping.ONION), 3), r);
        }

        @Test
        void quantityAndExtrasAreOptional() {
            assertEquals(new PizzaRequest(MenuItem.CHEESE, Size.SMALL, List.of(), 1), PizzaRequest.parse("cheese/small"));
        }

        @ParameterizedTest
        @ValueSource(strings = {"cheese", "cheese/huge", "calzone/small", "cheese/small/mushroom",
                "cheese/small/+anchovy", "a/b/c/d"})
        void rejectsMalformedSpecs(String spec) {
            assertThrows(IllegalArgumentException.class, () -> PizzaRequest.parse(spec));
        }
    }

    @Nested
    class Config {

        @Test
        void defaultsWhenUnset() {
            assertEquals(ShopConfig.DEFAULT_TAX_RATE, ShopConfig.fromEnvironment(Map.of()).taxRate());
        }

        @Test
        void readsTheEnvironmentVariable() {
            assertEquals(new BigDecimal("0.1"),
                    ShopConfig.fromEnvironment(Map.of(ShopConfig.TAX_RATE_VARIABLE, " 0.1 ")).taxRate());
        }

        @ParameterizedTest
        @ValueSource(strings = {"abc", "1", "-0.2"})
        void rejectsInvalidRates(String raw) {
            assertThrows(IllegalArgumentException.class,
                    () -> ShopConfig.fromEnvironment(Map.of(ShopConfig.TAX_RATE_VARIABLE, raw)));
        }
    }
}
