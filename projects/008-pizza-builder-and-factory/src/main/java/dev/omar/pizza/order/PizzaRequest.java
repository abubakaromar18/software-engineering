package dev.omar.pizza.order;

import dev.omar.pizza.domain.Size;
import dev.omar.pizza.domain.Topping;
import dev.omar.pizza.store.MenuItem;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * What a customer asked for, before any store has seen it. Parsed from the compact CLI syntax
 * {@code [N:]item/size[/+topping+topping...]}, for example {@code 2:pepperoni/large/+mushroom}.
 */
public record PizzaRequest(MenuItem item, Size size, List<Topping> extras, int quantity) {

    private static final Pattern QUANTITY = Pattern.compile("^(\\d+):(.+)$");

    public PizzaRequest {
        Objects.requireNonNull(item, "item");
        Objects.requireNonNull(size, "size");
        extras = List.copyOf(extras);
    }

    public static PizzaRequest parse(String spec) {
        Objects.requireNonNull(spec, "spec");
        String body = spec.trim();
        int quantity = 1;
        Matcher m = QUANTITY.matcher(body);
        if (m.matches()) {
            quantity = Integer.parseInt(m.group(1));
            body = m.group(2);
        }
        String[] parts = body.split("/");
        if (parts.length < 2 || parts.length > 3) {
            throw new IllegalArgumentException("Expected [N:]item/size[/+topping...] but got '" + spec + "'");
        }
        List<Topping> extras = new ArrayList<>();
        if (parts.length == 3) {
            if (!parts[2].startsWith("+")) {
                throw new IllegalArgumentException("Extra toppings must start with '+': '" + parts[2] + "'");
            }
            for (String name : parts[2].substring(1).split("\\+")) {
                extras.add(Topping.parse(name));
            }
        }
        return new PizzaRequest(MenuItem.parse(parts[0]), Size.parse(parts[1]), extras, quantity);
    }
}
