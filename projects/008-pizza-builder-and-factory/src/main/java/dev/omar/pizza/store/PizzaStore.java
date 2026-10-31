package dev.omar.pizza.store;

import dev.omar.pizza.domain.Pizza;
import dev.omar.pizza.domain.Size;
import dev.omar.pizza.domain.Topping;
import dev.omar.pizza.ingredient.IngredientFactory;

import java.util.EnumSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * <b>Factory Method.</b> {@link #orderPizza} is the fixed ordering workflow; the one step that
 * varies, actually creating the pizza, is the abstract {@link #createPizza} that each regional
 * store overrides. Callers depend only on {@code PizzaStore} and never on a concrete pizza recipe.
 *
 * <p>The store is also a client of the Abstract Factory: it receives one {@link IngredientFactory}
 * in its constructor (dependency injection, so tests can pass their own) and uses it for every
 * base ingredient.
 */
public abstract class PizzaStore {

    private final IngredientFactory ingredients;

    protected PizzaStore(IngredientFactory ingredients) {
        this.ingredients = Objects.requireNonNull(ingredients, "ingredients");
    }

    /** Shown on receipts. */
    public abstract String name();

    /**
     * The factory method. Subclasses decide how a menu item becomes a pizza in their style.
     * Availability has already been checked when this is called.
     */
    protected abstract Pizza createPizza(MenuItem item, Size size);

    /** Sizes this store bakes. Defaults to all; override to restrict. */
    public Set<Size> availableSizes() {
        return EnumSet.allOf(Size.class);
    }

    /** Menu items this store bakes. Defaults to all; override to restrict. */
    public Set<MenuItem> menu() {
        return EnumSet.allOf(MenuItem.class);
    }

    /**
     * Template for every order: check availability, let the subclass create the pizza, then
     * apply the customer's extra toppings through {@link Pizza#toBuilder()} so the builder's
     * rules (portion limits) still apply to customisations.
     *
     * @throws UnsupportedOrderException  if this store does not offer the item or size
     * @throws dev.omar.pizza.domain.InvalidPizzaException if the extras break a pizza rule
     */
    public final Pizza orderPizza(MenuItem item, Size size, List<Topping> extraToppings) {
        Objects.requireNonNull(item, "item");
        Objects.requireNonNull(size, "size");
        Objects.requireNonNull(extraToppings, "extraToppings");
        if (!menu().contains(item)) {
            throw new UnsupportedOrderException(name() + " does not serve " + item.displayName());
        }
        if (!availableSizes().contains(size)) {
            throw new UnsupportedOrderException(name() + " does not bake " + size.displayName().toLowerCase()
                    + " pizzas; available: " + availableSizes());
        }
        Pizza pizza = createPizza(item, size);
        if (extraToppings.isEmpty()) {
            return pizza;
        }
        return pizza.toBuilder().addToppings(extraToppings).build();
    }

    public final Pizza orderPizza(MenuItem item, Size size) {
        return orderPizza(item, size, List.of());
    }

    /**
     * Shared starting point for subclasses: the menu item's toppings on this store's ingredient
     * family. Subclasses adjust the returned builder rather than repeating the common part.
     */
    protected final Pizza.Builder recipe(String stylePrefix, MenuItem item, Size size) {
        return Pizza.builder()
                .name(stylePrefix + " " + item.displayName())
                .size(size)
                .dough(ingredients.createDough())
                .sauce(ingredients.createSauce())
                .cheese(ingredients.createCheese())
                .bake(ingredients.bakeProfile())
                .addToppings(item.toppings());
    }
}
