package dev.omar.pizza.domain;

import dev.omar.pizza.domain.Ingredients.BakeProfile;
import dev.omar.pizza.domain.Ingredients.Cheese;
import dev.omar.pizza.domain.Ingredients.Dough;
import dev.omar.pizza.domain.Ingredients.Sauce;
import dev.omar.pizza.domain.Ingredients.Style;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.time.Duration;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Tests for the Builder pattern: fluent construction, defaults, validation, immutability. */
class PizzaBuilderTest {

    private static final Dough DOUGH = new Dough("Test dough", Money.of("4.00"), Style.NEW_YORK);
    private static final Sauce SAUCE = new Sauce("Test sauce", Money.of("1.00"), Style.NEW_YORK);
    private static final Cheese CHEESE = new Cheese("Test cheese", Money.of("2.00"), Style.NEW_YORK);
    private static final BakeProfile BAKE = new BakeProfile(250, Duration.ofMinutes(10));

    /** A builder with every required field set; tests change only what they care about. */
    private static Pizza.Builder valid() {
        return Pizza.builder().name("Test").size(Size.SMALL)
                .dough(DOUGH).sauce(SAUCE).cheese(CHEESE).bake(BAKE);
    }

    @Nested
    class Construction {

        @Test
        void buildsAPizzaFromAFluentChain() {
            Pizza pizza = valid().addTopping(Topping.MUSHROOM).addTopping(Topping.ONION).build();

            assertEquals("Test", pizza.name());
            assertEquals(Size.SMALL, pizza.size());
            assertEquals(List.of(Topping.MUSHROOM, Topping.ONION), pizza.toppings());
        }

        @Test
        void defaultsToEightSlices() {
            assertEquals(Pizza.DEFAULT_SLICES, valid().build().slices());
        }

        @Test
        void addingAToppingTwiceMakesADoublePortion() {
            Pizza pizza = valid().addTopping(Topping.PEPPERONI).addTopping(Topping.PEPPERONI).build();
            assertEquals(Map.of(Topping.PEPPERONI, 2), pizza.toppingPortions());
            assertTrue(pizza.description().contains("Pepperoni x2"));
        }

        @Test
        void removeToppingTakesOffOnePortionAndIgnoresAbsentToppings() {
            Pizza pizza = valid()
                    .addTopping(Topping.HAM).addTopping(Topping.HAM)
                    .removeTopping(Topping.HAM)
                    .removeTopping(Topping.PINEAPPLE)
                    .build();
            assertEquals(List.of(Topping.HAM), pizza.toppings());
        }
    }

    @Nested
    class Validation {

        @Test
        void reportsEveryMissingFieldAtOnce() {
            InvalidPizzaException e = assertThrows(InvalidPizzaException.class, () -> Pizza.builder().build());
            assertEquals(List.of(
                    "name is required", "size is required", "dough is required",
                    "sauce is required", "cheese is required", "bake profile is required"), e.violations());
        }

        @Test
        void rejectsBlankName() {
            InvalidPizzaException e = assertThrows(InvalidPizzaException.class, () -> valid().name("  ").build());
            assertEquals(List.of("name is required"), e.violations());
        }

        @Test
        void rejectsATripleTopping() {
            Pizza.Builder builder = valid().addToppings(List.of(Topping.HAM, Topping.HAM, Topping.HAM));
            InvalidPizzaException e = assertThrows(InvalidPizzaException.class, builder::build);
            assertEquals(List.of("Ham added 3 times; max is 2"), e.violations());
        }

        @Test
        void rejectsTooManyPortionsInTotal() {
            Pizza.Builder builder = valid().addToppings(List.of(
                    Topping.HAM, Topping.MUSHROOM, Topping.ONION, Topping.BASIL, Topping.SAUSAGE,
                    Topping.PEPPERONI, Topping.PINEAPPLE, Topping.JALAPENO, Topping.BLACK_OLIVE));
            InvalidPizzaException e = assertThrows(InvalidPizzaException.class, builder::build);
            assertEquals(List.of("at most 8 topping portions allowed but got 9"), e.violations());
        }

        @Test
        void acceptsExactlyTheMaximumNumberOfPortions() {
            Pizza pizza = valid().addToppings(List.of(
                    Topping.HAM, Topping.HAM, Topping.MUSHROOM, Topping.MUSHROOM,
                    Topping.ONION, Topping.ONION, Topping.BASIL, Topping.BASIL)).build();
            assertEquals(Pizza.MAX_TOTAL_PORTIONS, pizza.toppings().size());
        }

        @ParameterizedTest
        @ValueSource(ints = {-1, 17})
        void rejectsSliceCountsOutOfRange(int slices) {
            assertThrows(InvalidPizzaException.class, () -> valid().slices(slices).build());
        }

        @Test
        void rejectsIngredientsFromDifferentFamilies() {
            Dough chicago = new Dough("Deep dish", Money.of("5.00"), Style.CHICAGO);
            InvalidPizzaException e = assertThrows(InvalidPizzaException.class, () -> valid().dough(chicago).build());
            assertEquals(List.of("dough, sauce and cheese must share one style but were CHICAGO, NEW_YORK, NEW_YORK"),
                    e.violations());
        }

        @Test
        void nullToppingFailsFast() {
            assertThrows(NullPointerException.class, () -> valid().addTopping(null));
        }
    }

    @Nested
    class Immutability {

        @Test
        void builtPizzaIsUnaffectedByLaterBuilderCalls() {
            Pizza.Builder builder = valid().addTopping(Topping.MUSHROOM);
            Pizza first = builder.build();
            builder.addTopping(Topping.ONION).size(Size.LARGE);

            assertEquals(List.of(Topping.MUSHROOM), first.toppings());
            assertEquals(Size.SMALL, first.size());
        }

        @Test
        void toppingListCannotBeModified() {
            Pizza pizza = valid().addTopping(Topping.HAM).build();
            assertThrows(UnsupportedOperationException.class, () -> pizza.toppings().add(Topping.BASIL));
            assertThrows(UnsupportedOperationException.class, () -> pizza.toppingPortions().put(Topping.BASIL, 1));
        }

        @Test
        void toBuilderCopiesWithoutChangingTheOriginal() {
            Pizza original = valid().addTopping(Topping.HAM).build();
            Pizza bigger = original.toBuilder().size(Size.LARGE).addTopping(Topping.PINEAPPLE).build();

            assertEquals(original, original.toBuilder().build());
            assertNotEquals(original, bigger);
            assertEquals(List.of(Topping.HAM), original.toppings());
            assertEquals(List.of(Topping.HAM, Topping.PINEAPPLE), bigger.toppings());
        }

        @Test
        void equalityIgnoresToppingOrder() {
            Pizza a = valid().addTopping(Topping.HAM).addTopping(Topping.BASIL).build();
            Pizza b = valid().addTopping(Topping.BASIL).addTopping(Topping.HAM).build();
            assertEquals(a, b);
            assertEquals(a.hashCode(), b.hashCode());
        }
    }

    @Nested
    class Pricing {

        @Test
        void smallPriceIsBasePlusToppings() {
            // 4.00 + 1.00 + 2.00 + 1.50 (pepperoni) + 1.00 (mushroom)
            Pizza pizza = valid().addTopping(Topping.PEPPERONI).addTopping(Topping.MUSHROOM).build();
            assertEquals(Money.of("9.50"), pizza.price());
        }

        @Test
        void sizeMultiplierScalesTheWholePizza() {
            Pizza.Builder builder = valid().addTopping(Topping.PEPPERONI);
            // small is 8.50; scaling happens once on the total, so only one rounding step
            assertEquals(Money.of("12.75"), builder.size(Size.LARGE).build().price());
            // 8.50 * 1.25 = 10.625: the half cent rounds to the even neighbour, 10.62
            assertEquals(Money.of("10.62"), builder.size(Size.MEDIUM).build().price());
        }

        @Test
        void vegetarianOnlyWhenEveryToppingIs() {
            assertTrue(valid().addTopping(Topping.MUSHROOM).build().isVegetarian());
            assertTrue(valid().build().isVegetarian());
            assertFalse(valid().addTopping(Topping.MUSHROOM).addTopping(Topping.HAM).build().isVegetarian());
        }
    }
}
