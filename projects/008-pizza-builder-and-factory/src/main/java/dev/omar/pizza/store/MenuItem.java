package dev.omar.pizza.store;

import dev.omar.pizza.domain.Topping;

import java.util.List;
import java.util.Locale;

/** The house recipes. A recipe only lists toppings; the store decides dough, sauce and cheese. */
public enum MenuItem {
    CHEESE("Cheese", List.of()),
    MARGHERITA("Margherita", List.of(Topping.BASIL)),
    PEPPERONI("Pepperoni", List.of(Topping.PEPPERONI)),
    VEGGIE("Garden Veggie", List.of(Topping.MUSHROOM, Topping.ONION, Topping.GREEN_PEPPER, Topping.BLACK_OLIVE)),
    MEAT_LOVERS("Meat Lovers", List.of(Topping.PEPPERONI, Topping.SAUSAGE, Topping.HAM)),
    HAWAIIAN("Hawaiian", List.of(Topping.HAM, Topping.PINEAPPLE));

    private final String displayName;
    private final List<Topping> toppings;

    MenuItem(String displayName, List<Topping> toppings) {
        this.displayName = displayName;
        this.toppings = toppings;
    }

    public String displayName() {
        return displayName;
    }

    public List<Topping> toppings() {
        return toppings;
    }

    /** Case-insensitive lookup; dashes and spaces are treated as underscores. */
    public static MenuItem parse(String text) {
        String key = text.trim().toUpperCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        try {
            return valueOf(key);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Unknown menu item '" + text + "'", e);
        }
    }
}
