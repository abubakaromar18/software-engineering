package dev.omar.pizza.order;

import dev.omar.pizza.domain.Money;
import dev.omar.pizza.domain.Pizza;

import java.util.Objects;

/** One pizza and how many of it. */
public record OrderLine(Pizza pizza, int quantity) {

    public static final int MAX_QUANTITY = 20;

    public OrderLine {
        Objects.requireNonNull(pizza, "pizza");
        if (quantity < 1 || quantity > MAX_QUANTITY) {
            throw new IllegalArgumentException("quantity must be 1.." + MAX_QUANTITY + " but was " + quantity);
        }
    }

    public Money total() {
        return pizza.price().times(quantity);
    }
}
