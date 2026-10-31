package dev.omar.pizza.store;

import dev.omar.pizza.domain.Pizza;
import dev.omar.pizza.domain.Size;
import dev.omar.pizza.ingredient.IngredientFactory;
import dev.omar.pizza.ingredient.NewYorkIngredientFactory;

/** Every size, the whole menu, cut into eight foldable slices. */
public final class NewYorkPizzaStore extends PizzaStore {

    public NewYorkPizzaStore() {
        this(new NewYorkIngredientFactory());
    }

    public NewYorkPizzaStore(IngredientFactory ingredients) {
        super(ingredients);
    }

    @Override
    public String name() {
        return "Brooklyn Slice Co. (New York)";
    }

    @Override
    protected Pizza createPizza(MenuItem item, Size size) {
        return recipe("New York Style", item, size)
                .slices(8)
                .build();
    }
}
