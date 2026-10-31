package dev.omar.pizza.domain;

import java.time.Duration;
import java.util.Objects;

/**
 * The base ingredients of a pizza: the products an {@code IngredientFactory} creates.
 *
 * <p>Each record carries the {@link Style} it belongs to. That tag is what lets the tests prove
 * the Abstract Factory guarantee: one factory never mixes products from two families.
 */
public final class Ingredients {

    private Ingredients() {
    }

    /** A regional family of ingredients. */
    public enum Style {
        NEW_YORK, CHICAGO, NEAPOLITAN
    }

    /** Common shape of every base ingredient. */
    public sealed interface Ingredient permits Dough, Sauce, Cheese {
        String name();

        Money price();

        Style style();
    }

    public record Dough(String name, Money price, Style style) implements Ingredient {
        public Dough {
            requireFields(name, price, style);
        }
    }

    public record Sauce(String name, Money price, Style style) implements Ingredient {
        public Sauce {
            requireFields(name, price, style);
        }
    }

    public record Cheese(String name, Money price, Style style) implements Ingredient {
        public Cheese {
            requireFields(name, price, style);
        }
    }

    /** How a family's pizzas are baked. Part of the family, so it comes from the same factory. */
    public record BakeProfile(int ovenCelsius, Duration time) {
        public BakeProfile {
            Objects.requireNonNull(time, "time");
            if (ovenCelsius <= 0 || time.isNegative() || time.isZero()) {
                throw new IllegalArgumentException("Bake profile needs a positive temperature and time");
            }
        }

        @Override
        public String toString() {
            long seconds = time.toSeconds();
            String duration = seconds % 60 == 0 ? (seconds / 60) + " min" : seconds + " s";
            return ovenCelsius + " C for " + duration;
        }
    }

    private static void requireFields(String name, Money price, Style style) {
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(price, "price");
        Objects.requireNonNull(style, "style");
        if (name.isBlank()) {
            throw new IllegalArgumentException("Ingredient name must not be blank");
        }
    }
}
