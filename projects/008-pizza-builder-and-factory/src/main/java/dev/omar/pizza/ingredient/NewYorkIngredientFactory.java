package dev.omar.pizza.ingredient;

import dev.omar.pizza.domain.Ingredients.BakeProfile;
import dev.omar.pizza.domain.Ingredients.Cheese;
import dev.omar.pizza.domain.Ingredients.Dough;
import dev.omar.pizza.domain.Ingredients.Sauce;
import dev.omar.pizza.domain.Ingredients.Style;
import dev.omar.pizza.domain.Money;

import java.time.Duration;

/** Concrete factory: thin, foldable crust, cooked tomato sauce, low-moisture mozzarella. */
public final class NewYorkIngredientFactory implements IngredientFactory {

    @Override
    public Style style() {
        return Style.NEW_YORK;
    }

    @Override
    public Dough createDough() {
        return new Dough("Thin hand-tossed dough", Money.of("4.00"), Style.NEW_YORK);
    }

    @Override
    public Sauce createSauce() {
        return new Sauce("Oregano tomato sauce", Money.of("1.00"), Style.NEW_YORK);
    }

    @Override
    public Cheese createCheese() {
        return new Cheese("Low-moisture mozzarella", Money.of("2.00"), Style.NEW_YORK);
    }

    @Override
    public BakeProfile bakeProfile() {
        return new BakeProfile(290, Duration.ofMinutes(12));
    }
}
