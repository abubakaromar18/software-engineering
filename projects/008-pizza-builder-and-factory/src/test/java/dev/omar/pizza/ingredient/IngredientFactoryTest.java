package dev.omar.pizza.ingredient;

import dev.omar.pizza.domain.Ingredients.Ingredient;
import dev.omar.pizza.domain.Ingredients.Style;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Tests for the Abstract Factory pattern: each factory yields one consistent family. */
class IngredientFactoryTest {

    static Stream<Arguments> factories() {
        return Stream.of(
                Arguments.of(new NewYorkIngredientFactory(), Style.NEW_YORK),
                Arguments.of(new ChicagoIngredientFactory(), Style.CHICAGO),
                Arguments.of(new NeapolitanIngredientFactory(), Style.NEAPOLITAN));
    }

    @ParameterizedTest
    @MethodSource("factories")
    void everyProductBelongsToTheFactorysFamily(IngredientFactory factory, Style expected) {
        assertEquals(expected, factory.style());
        List<Ingredient> products = List.of(factory.createDough(), factory.createSauce(), factory.createCheese());
        products.forEach(p -> assertEquals(expected, p.style(), p.name()));
    }

    @ParameterizedTest
    @MethodSource("factories")
    void productsAreEqualValuesOnEveryCall(IngredientFactory factory, Style ignored) {
        assertEquals(factory.createDough(), factory.createDough());
        assertEquals(factory.bakeProfile(), factory.bakeProfile());
    }

    @Test
    void familiesAreDistinct() {
        Set<String> doughs = factories()
                .map(a -> ((IngredientFactory) a.get()[0]).createDough().name())
                .collect(Collectors.toSet());
        assertEquals(3, doughs.size());
    }

    @Test
    void bakeProfilesMatchTheirStyle() {
        // Neapolitan is the hottest, fastest bake; deep dish the coolest, slowest.
        var naples = new NeapolitanIngredientFactory().bakeProfile();
        var chicago = new ChicagoIngredientFactory().bakeProfile();
        assertTrue(naples.ovenCelsius() > chicago.ovenCelsius());
        assertTrue(naples.time().compareTo(chicago.time()) < 0);
        assertEquals("485 C for 90 s", naples.toString());
        assertEquals("220 C for 35 min", chicago.toString());
    }
}
