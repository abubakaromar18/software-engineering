package dev.omar.pizza.store;

import dev.omar.pizza.domain.Pizza;
import dev.omar.pizza.domain.Size;
import dev.omar.pizza.ingredient.ChicagoIngredientFactory;
import dev.omar.pizza.ingredient.IngredientFactory;

import java.util.EnumSet;
import java.util.Set;

/** Deep dish only comes in medium and large pans, and is cut into six wedges. */
public final class ChicagoPizzaStore extends PizzaStore {

    public ChicagoPizzaStore() {
        this(new ChicagoIngredientFactory());
    }

    public ChicagoPizzaStore(IngredientFactory ingredients) {
        super(ingredients);
    }

    @Override
    public String name() {
        return "Lakeshore Deep Dish (Chicago)";
    }

    @Override
    public Set<Size> availableSizes() {
        return EnumSet.of(Size.MEDIUM, Size.LARGE);
    }

    @Override
    protected Pizza createPizza(MenuItem item, Size size) {
        return recipe("Chicago Deep Dish", item, size)
                .slices(6)
                .build();
    }
}
