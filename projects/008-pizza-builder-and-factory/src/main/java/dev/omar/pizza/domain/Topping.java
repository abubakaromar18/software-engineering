package dev.omar.pizza.domain;

import java.util.Locale;

/** Toppings a customer can add. Prices are for a small pizza; {@link Size} scales them up. */
public enum Topping {
    PEPPERONI("Pepperoni", 150, false),
    SAUSAGE("Italian sausage", 175, false),
    HAM("Ham", 150, false),
    MUSHROOM("Mushrooms", 100, true),
    ONION("Red onion", 75, true),
    GREEN_PEPPER("Green pepper", 75, true),
    BLACK_OLIVE("Black olives", 100, true),
    BASIL("Fresh basil", 50, true),
    JALAPENO("Jalapenos", 75, true),
    PINEAPPLE("Pineapple", 100, true);

    private final String displayName;
    private final Money price;
    private final boolean vegetarian;

    Topping(String displayName, long priceCents, boolean vegetarian) {
        this.displayName = displayName;
        this.price = Money.ofCents(priceCents);
        this.vegetarian = vegetarian;
    }

    public String displayName() {
        return displayName;
    }

    public Money price() {
        return price;
    }

    public boolean isVegetarian() {
        return vegetarian;
    }

    /** Case-insensitive lookup; dashes and spaces are treated as underscores. */
    public static Topping parse(String text) {
        String key = text.trim().toUpperCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
        try {
            return valueOf(key);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Unknown topping '" + text + "'", e);
        }
    }
}
