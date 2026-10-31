package dev.omar.pizza.store;

import dev.omar.pizza.domain.Pizza;
import dev.omar.pizza.domain.Size;
import dev.omar.pizza.domain.Topping;
import dev.omar.pizza.ingredient.IngredientFactory;
import dev.omar.pizza.ingredient.NeapolitanIngredientFactory;

import java.util.EnumSet;
import java.util.Set;

/**
 * Personal-size pies, served uncut, with a short traditional menu. Every pie is finished with
 * fresh basil, which shows a subclass customising the shared recipe instead of replacing it.
 */
public final class NeapolitanPizzaStore extends PizzaStore {

    public NeapolitanPizzaStore() {
        this(new NeapolitanIngredientFactory());
    }

    public NeapolitanPizzaStore(IngredientFactory ingredients) {
        super(ingredients);
    }

    @Override
    public String name() {
        return "Forno Vesuvio (Naples)";
    }

    @Override
    public Set<Size> availableSizes() {
        return EnumSet.of(Size.SMALL, Size.MEDIUM);
    }

    @Override
    public Set<MenuItem> menu() {
        return EnumSet.complementOf(EnumSet.of(MenuItem.MEAT_LOVERS, MenuItem.HAWAIIAN));
    }

    @Override
    protected Pizza createPizza(MenuItem item, Size size) {
        Pizza.Builder builder = recipe("Neapolitan", item, size).slices(0);
        if (!item.toppings().contains(Topping.BASIL)) {
            builder.addTopping(Topping.BASIL);
        }
        return builder.build();
    }
}
