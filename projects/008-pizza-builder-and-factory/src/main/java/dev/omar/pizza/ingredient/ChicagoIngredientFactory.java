package dev.omar.pizza.ingredient;

import dev.omar.pizza.domain.Ingredients.BakeProfile;
import dev.omar.pizza.domain.Ingredients.Cheese;
import dev.omar.pizza.domain.Ingredients.Dough;
import dev.omar.pizza.domain.Ingredients.Sauce;
import dev.omar.pizza.domain.Ingredients.Style;
import dev.omar.pizza.domain.Money;

import java.time.Duration;

/** Concrete factory: buttery deep-dish crust, chunky tomato sauce, sliced mozzarella. */
public final class ChicagoIngredientFactory implements IngredientFactory {

    @Override
    public Style style() {
        return Style.CHICAGO;
    }

    @Override
    public Dough createDough() {
        return new Dough("Buttery deep-dish crust", Money.of("5.50"), Style.CHICAGO);
    }

    @Override
    public Sauce createSauce() {
        return new Sauce("Chunky crushed-tomato sauce", Money.of("1.50"), Style.CHICAGO);
    }

    @Override
    public Cheese createCheese() {
        return new Cheese("Sliced whole-milk mozzarella", Money.of("2.50"), Style.CHICAGO);
    }

    @Override
    public BakeProfile bakeProfile() {
        return new BakeProfile(220, Duration.ofMinutes(35));
    }
}
