package dev.omar.pizza.store;

import dev.omar.pizza.domain.Ingredients.BakeProfile;
import dev.omar.pizza.domain.Ingredients.Cheese;
import dev.omar.pizza.domain.Ingredients.Dough;
import dev.omar.pizza.domain.Ingredients.Sauce;
import dev.omar.pizza.domain.Ingredients.Style;
import dev.omar.pizza.domain.InvalidPizzaException;
import dev.omar.pizza.domain.Money;
import dev.omar.pizza.domain.Pizza;
import dev.omar.pizza.domain.Size;
import dev.omar.pizza.domain.Topping;
import dev.omar.pizza.ingredient.IngredientFactory;
import dev.omar.pizza.ingredient.NewYorkIngredientFactory;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

import java.time.Duration;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Tests for the Factory Method pattern (stores) and the simple factory (PizzaStores). */
class PizzaStoreTest {

    @Nested
    class FactoryMethod {

        @Test
        void newYorkMakesThinEightSliceAnySize() {
            Pizza pizza = new NewYorkPizzaStore().orderPizza(MenuItem.PEPPERONI, Size.SMALL);
            assertEquals("New York Style Pepperoni", pizza.name());
            assertEquals(Style.NEW_YORK, pizza.dough().style());
            assertEquals(8, pizza.slices());
            assertEquals(List.of(Topping.PEPPERONI), pizza.toppings());
        }

        @Test
        void chicagoMakesSixWedgeDeepDish() {
            Pizza pizza = new ChicagoPizzaStore().orderPizza(MenuItem.MEAT_LOVERS, Size.LARGE);
            assertEquals("Chicago Deep Dish Meat Lovers", pizza.name());
            assertEquals(Style.CHICAGO, pizza.cheese().style());
            assertEquals(6, pizza.slices());
        }

        @Test
        void neapolitanIsUncutAndAlwaysHasBasil() {
            Pizza veggie = new NeapolitanPizzaStore().orderPizza(MenuItem.VEGGIE, Size.MEDIUM);
            assertEquals(0, veggie.slices());
            assertTrue(veggie.toppings().contains(Topping.BASIL));

            Pizza margherita = new NeapolitanPizzaStore().orderPizza(MenuItem.MARGHERITA, Size.SMALL);
            assertEquals(List.of(Topping.BASIL), margherita.toppings(), "basil is not doubled");
        }

        @Test
        void sameMenuItemDiffersByStore() {
            Pizza ny = new NewYorkPizzaStore().orderPizza(MenuItem.CHEESE, Size.MEDIUM);
            Pizza chi = new ChicagoPizzaStore().orderPizza(MenuItem.CHEESE, Size.MEDIUM);
            assertEquals(Money.of("8.75"), ny.price());   // (4.00 + 1.00 + 2.00) * 1.25
            assertEquals(Money.of("11.88"), chi.price()); // (5.50 + 1.50 + 2.50) * 1.25 = 11.875 -> even
        }
    }

    @Nested
    class TemplateWorkflow {

        @Test
        void extrasAreAddedOnTopOfTheRecipe() {
            Pizza pizza = new NewYorkPizzaStore()
                    .orderPizza(MenuItem.PEPPERONI, Size.LARGE, List.of(Topping.PEPPERONI, Topping.MUSHROOM));
            assertEquals(List.of(Topping.PEPPERONI, Topping.PEPPERONI, Topping.MUSHROOM), pizza.toppings());
        }

        @Test
        void extrasStillObeyTheBuilderRules() {
            PizzaStore store = new NewYorkPizzaStore();
            InvalidPizzaException e = assertThrows(InvalidPizzaException.class,
                    () -> store.orderPizza(MenuItem.PEPPERONI, Size.LARGE, List.of(Topping.PEPPERONI, Topping.PEPPERONI)));
            assertEquals(List.of("Pepperoni added 3 times; max is 2"), e.violations());
        }

        @Test
        void chicagoRejectsSmall() {
            UnsupportedOrderException e = assertThrows(UnsupportedOrderException.class,
                    () -> new ChicagoPizzaStore().orderPizza(MenuItem.CHEESE, Size.SMALL));
            assertTrue(e.getMessage().contains("does not bake small pizzas"), e.getMessage());
        }

        @Test
        void neapolitanRejectsLargeAndOffMenuItems() {
            PizzaStore store = new NeapolitanPizzaStore();
            assertThrows(UnsupportedOrderException.class, () -> store.orderPizza(MenuItem.CHEESE, Size.LARGE));
            UnsupportedOrderException e = assertThrows(UnsupportedOrderException.class,
                    () -> store.orderPizza(MenuItem.HAWAIIAN, Size.SMALL));
            assertEquals("Forno Vesuvio (Naples) does not serve Hawaiian", e.getMessage());
        }

        @Test
        void storeUsesTheInjectedIngredientFactory() {
            IngredientFactory stub = new IngredientFactory() {
                @Override
                public Style style() {
                    return Style.NEW_YORK;
                }

                @Override
                public Dough createDough() {
                    return new Dough("Stub dough", Money.ofCents(1), Style.NEW_YORK);
                }

                @Override
                public Sauce createSauce() {
                    return new Sauce("Stub sauce", Money.ofCents(1), Style.NEW_YORK);
                }

                @Override
                public Cheese createCheese() {
                    return new Cheese("Stub cheese", Money.ofCents(1), Style.NEW_YORK);
                }

                @Override
                public BakeProfile bakeProfile() {
                    return new BakeProfile(100, Duration.ofMinutes(1));
                }
            };
            Pizza pizza = new NewYorkPizzaStore(stub).orderPizza(MenuItem.CHEESE, Size.SMALL);
            assertEquals("Stub dough", pizza.dough().name());
            assertEquals(Money.ofCents(3), pizza.price());
        }

        @Test
        void aMismatchedFactoryIsCaughtByTheBuilder() {
            // A broken factory that mixes families: the builder's invariant stops it.
            IngredientFactory broken = new IngredientFactory() {
                private final IngredientFactory ny = new NewYorkIngredientFactory();

                @Override
                public Style style() {
                    return Style.NEW_YORK;
                }

                @Override
                public Dough createDough() {
                    return new Dough("Wrong dough", Money.ofCents(1), Style.CHICAGO);
                }

                @Override
                public Sauce createSauce() {
                    return ny.createSauce();
                }

                @Override
                public Cheese createCheese() {
                    return ny.createCheese();
                }

                @Override
                public BakeProfile bakeProfile() {
                    return ny.bakeProfile();
                }
            };
            assertThrows(InvalidPizzaException.class,
                    () -> new NewYorkPizzaStore(broken).orderPizza(MenuItem.CHEESE, Size.SMALL));
        }
    }

    @Nested
    class SimpleFactory {

        @ParameterizedTest
        @EnumSource(Region.class)
        void everyRegionHasAStore(Region region) {
            PizzaStore store = PizzaStores.forRegion(region);
            Pizza pizza = store.orderPizza(MenuItem.CHEESE, Size.MEDIUM);
            assertEquals(expectedStyle(region), pizza.dough().style());
        }

        @Test
        void returnsTheExpectedConcreteTypes() {
            assertInstanceOf(NewYorkPizzaStore.class, PizzaStores.forRegion(Region.NEW_YORK));
            assertInstanceOf(ChicagoPizzaStore.class, PizzaStores.forRegion(Region.CHICAGO));
            assertInstanceOf(NeapolitanPizzaStore.class, PizzaStores.forRegion(Region.NAPLES));
        }

        @Test
        void regionParsingAcceptsAliases() {
            assertEquals(Region.NEW_YORK, Region.parse("NYC"));
            assertEquals(Region.CHICAGO, Region.parse(" chi "));
            assertEquals(Region.NAPLES, Region.parse("napoli"));
            assertEquals(Region.NAPLES, Region.parse("naples"));
            assertThrows(IllegalArgumentException.class, () -> Region.parse("detroit"));
        }

        private Style expectedStyle(Region region) {
            return switch (region) {
                case NEW_YORK -> Style.NEW_YORK;
                case CHICAGO -> Style.CHICAGO;
                case NAPLES -> Style.NEAPOLITAN;
            };
        }
    }
}
