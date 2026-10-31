package dev.omar.pizza.ingredient;

import dev.omar.pizza.domain.Ingredients.BakeProfile;
import dev.omar.pizza.domain.Ingredients.Cheese;
import dev.omar.pizza.domain.Ingredients.Dough;
import dev.omar.pizza.domain.Ingredients.Sauce;
import dev.omar.pizza.domain.Ingredients.Style;
import dev.omar.pizza.domain.Money;

import java.time.Duration;

/** Concrete factory: 00-flour dough, raw San Marzano sauce, fior di latte, a very hot wood oven. */
public final class NeapolitanIngredientFactory implements IngredientFactory {

    @Override
    public Style style() {
        return Style.NEAPOLITAN;
    }

    @Override
    public Dough createDough() {
        return new Dough("00-flour dough, 48h proof", Money.of("4.50"), Style.NEAPOLITAN);
    }

    @Override
    public Sauce createSauce() {
        return new Sauce("Raw San Marzano tomatoes", Money.of("1.75"), Style.NEAPOLITAN);
    }

    @Override
    public Cheese createCheese() {
        return new Cheese("Fior di latte", Money.of("2.75"), Style.NEAPOLITAN);
    }

    @Override
    public BakeProfile bakeProfile() {
        return new BakeProfile(485, Duration.ofSeconds(90));
    }
}
