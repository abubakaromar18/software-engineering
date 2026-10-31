package dev.omar.pizza.domain;

import dev.omar.pizza.domain.Ingredients.BakeProfile;
import dev.omar.pizza.domain.Ingredients.Cheese;
import dev.omar.pizza.domain.Ingredients.Dough;
import dev.omar.pizza.domain.Ingredients.Sauce;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * An immutable pizza. The only way to make one is {@link Builder}, which checks every business
 * rule in {@link Builder#build()} so an invalid {@code Pizza} can never exist.
 */
public final class Pizza {

    /** No topping may be added more than twice ("double pepperoni" is fine, triple is not). */
    public static final int MAX_PORTIONS_PER_TOPPING = 2;
    /** Total topping portions on one pizza, counting a double topping as two. */
    public static final int MAX_TOTAL_PORTIONS = 8;
    public static final int MAX_SLICES = 16;
    public static final int DEFAULT_SLICES = 8;

    private final String name;
    private final Size size;
    private final Dough dough;
    private final Sauce sauce;
    private final Cheese cheese;
    private final List<Topping> toppings;
    private final BakeProfile bakeProfile;
    private final int slices;

    private Pizza(Builder builder) {
        this.name = builder.name;
        this.size = builder.size;
        this.dough = builder.dough;
        this.sauce = builder.sauce;
        this.cheese = builder.cheese;
        this.toppings = List.copyOf(builder.toppings);
        this.bakeProfile = builder.bakeProfile;
        this.slices = builder.slices;
    }

    public static Builder builder() {
        return new Builder();
    }

    /** Starts a new builder pre-filled with this pizza, for "same again, but ..." changes. */
    public Builder toBuilder() {
        Builder copy = new Builder()
                .name(name).size(size).dough(dough).sauce(sauce).cheese(cheese)
                .bake(bakeProfile).slices(slices);
        copy.toppings.addAll(toppings);
        return copy;
    }

    public String name() {
        return name;
    }

    public Size size() {
        return size;
    }

    public Dough dough() {
        return dough;
    }

    public Sauce sauce() {
        return sauce;
    }

    public Cheese cheese() {
        return cheese;
    }

    /** Toppings in the order they were added; a double topping appears twice. */
    public List<Topping> toppings() {
        return toppings;
    }

    /** Portions per topping, in menu order. */
    public Map<Topping, Integer> toppingPortions() {
        Map<Topping, Integer> portions = new EnumMap<>(Topping.class);
        toppings.forEach(t -> portions.merge(t, 1, Integer::sum));
        return Collections.unmodifiableMap(portions);
    }

    public BakeProfile bakeProfile() {
        return bakeProfile;
    }

    public int slices() {
        return slices;
    }

    public boolean isVegetarian() {
        return toppings.stream().allMatch(Topping::isVegetarian);
    }

    /** Base ingredients plus toppings, scaled once by the size multiplier (one rounding step). */
    public Money price() {
        Money base = dough.price().plus(sauce.price()).plus(cheese.price());
        Money withToppings = toppings.stream().map(Topping::price).reduce(base, Money::plus);
        return withToppings.times(size.priceMultiplier());
    }

    /** One-line, human-readable summary used on receipts. */
    public String description() {
        String toppingText = toppings.isEmpty() ? "no toppings" : toppingPortions().entrySet().stream()
                .map(e -> e.getValue() > 1 ? e.getKey().displayName() + " x" + e.getValue() : e.getKey().displayName())
                .collect(Collectors.joining(", "));
        String cut = slices == 0 ? "uncut" : slices + " slices";
        return String.format("%s %s (%d cm): %s, %s, %s; %s; %s",
                size.displayName(), name, size.diameterCm(),
                dough.name(), sauce.name(), cheese.name(), toppingText, cut);
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof Pizza other
                && slices == other.slices
                && name.equals(other.name)
                && size == other.size
                && dough.equals(other.dough)
                && sauce.equals(other.sauce)
                && cheese.equals(other.cheese)
                && toppingPortions().equals(other.toppingPortions())
                && bakeProfile.equals(other.bakeProfile);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, size, dough, sauce, cheese, toppingPortions(), bakeProfile, slices);
    }

    @Override
    public String toString() {
        return "Pizza[" + description() + "]";
    }

    /**
     * Fluent, mutable builder for {@link Pizza}.
     *
     * <p>Setters only record values; all validation happens in {@link #build()} and reports every
     * violation at once. That keeps the call chain readable and gives a caller (or an API layer)
     * one complete error list instead of fix-one-retry-repeat.
     */
    public static final class Builder {
        private String name;
        private Size size;
        private Dough dough;
        private Sauce sauce;
        private Cheese cheese;
        private BakeProfile bakeProfile;
        private int slices = DEFAULT_SLICES;
        private final List<Topping> toppings = new ArrayList<>();

        private Builder() {
        }

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder size(Size size) {
            this.size = size;
            return this;
        }

        public Builder dough(Dough dough) {
            this.dough = dough;
            return this;
        }

        public Builder sauce(Sauce sauce) {
            this.sauce = sauce;
            return this;
        }

        public Builder cheese(Cheese cheese) {
            this.cheese = cheese;
            return this;
        }

        public Builder bake(BakeProfile bakeProfile) {
            this.bakeProfile = bakeProfile;
            return this;
        }

        /** Number of slices to cut; 0 means the pizza is served uncut. */
        public Builder slices(int slices) {
            this.slices = slices;
            return this;
        }

        /** Adds one portion. Add the same topping twice for a double portion. */
        public Builder addTopping(Topping topping) {
            toppings.add(Objects.requireNonNull(topping, "topping"));
            return this;
        }

        public Builder addToppings(Collection<Topping> more) {
            more.forEach(this::addTopping);
            return this;
        }

        /** Removes one portion of the topping, if present. Removing an absent topping is a no-op. */
        public Builder removeTopping(Topping topping) {
            toppings.remove(topping);
            return this;
        }

        public Pizza build() {
            List<String> violations = new ArrayList<>();
            if (name == null || name.isBlank()) {
                violations.add("name is required");
            }
            requirePresent(size, "size", violations);
            requirePresent(dough, "dough", violations);
            requirePresent(sauce, "sauce", violations);
            requirePresent(cheese, "cheese", violations);
            requirePresent(bakeProfile, "bake profile", violations);
            checkSameStyle(violations);
            checkToppings(violations);
            if (slices < 0 || slices > MAX_SLICES) {
                violations.add("slices must be between 0 and " + MAX_SLICES + " but was " + slices);
            }
            if (!violations.isEmpty()) {
                throw new InvalidPizzaException(violations);
            }
            return new Pizza(this);
        }

        private static void requirePresent(Object value, String field, List<String> violations) {
            if (value == null) {
                violations.add(field + " is required");
            }
        }

        /** Dough, sauce and cheese must come from one family, whoever assembled them. */
        private void checkSameStyle(List<String> violations) {
            if (dough == null || sauce == null || cheese == null) {
                return;
            }
            if (dough.style() != sauce.style() || dough.style() != cheese.style()) {
                violations.add("dough, sauce and cheese must share one style but were "
                        + dough.style() + ", " + sauce.style() + ", " + cheese.style());
            }
        }

        private void checkToppings(List<String> violations) {
            if (toppings.size() > MAX_TOTAL_PORTIONS) {
                violations.add("at most " + MAX_TOTAL_PORTIONS + " topping portions allowed but got " + toppings.size());
            }
            Map<Topping, Long> counts = toppings.stream()
                    .collect(Collectors.groupingBy(t -> t, () -> new EnumMap<>(Topping.class), Collectors.counting()));
            counts.forEach((topping, count) -> {
                if (count > MAX_PORTIONS_PER_TOPPING) {
                    violations.add(topping.displayName() + " added " + count + " times; max is " + MAX_PORTIONS_PER_TOPPING);
                }
            });
        }
    }
}
