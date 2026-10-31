package dev.omar.pizza.domain;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Thrown by {@link Pizza.Builder#build()} with every rule the pizza breaks, not just the first. */
public final class InvalidPizzaException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    // ArrayList rather than List so the field is Serializable, as exceptions must be.
    private final ArrayList<String> violations;

    public InvalidPizzaException(List<String> violations) {
        super("Invalid pizza: " + String.join("; ", violations));
        this.violations = new ArrayList<>(violations);
    }

    public List<String> violations() {
        return Collections.unmodifiableList(violations);
    }
}
