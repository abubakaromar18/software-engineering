package dev.omar.pizza.order;

import dev.omar.pizza.domain.Money;

import java.math.BigDecimal;
import java.util.List;
import java.util.Objects;

/** An immutable order from one store: its lines plus the tax rate in force when it was placed. */
public record Order(String storeName, List<OrderLine> lines, BigDecimal taxRate) {

    public Order {
        Objects.requireNonNull(storeName, "storeName");
        Objects.requireNonNull(taxRate, "taxRate");
        lines = List.copyOf(lines);
        if (lines.isEmpty()) {
            throw new IllegalArgumentException("An order needs at least one line");
        }
        if (taxRate.signum() < 0 || taxRate.compareTo(BigDecimal.ONE) >= 0) {
            throw new IllegalArgumentException("taxRate must be in [0, 1) but was " + taxRate);
        }
    }

    public Money subtotal() {
        return lines.stream().map(OrderLine::total).reduce(Money.ZERO, Money::plus);
    }

    /** Tax is computed once on the subtotal, not per line, so rounding happens a single time. */
    public Money tax() {
        return subtotal().times(taxRate);
    }

    public Money total() {
        return subtotal().plus(tax());
    }

    public int pizzaCount() {
        return lines.stream().mapToInt(OrderLine::quantity).sum();
    }

    /** A plain-text receipt. */
    public String receipt() {
        StringBuilder out = new StringBuilder();
        out.append(storeName).append('\n');
        out.append("-".repeat(storeName.length())).append('\n');
        for (OrderLine line : lines) {
            out.append(String.format("%2d x %-58s %9s%n", line.quantity(), line.pizza().name()
                    + " (" + line.pizza().size().displayName() + ")", line.total()));
            out.append("       ").append(line.pizza().description()).append('\n');
            out.append("       bake: ").append(line.pizza().bakeProfile())
                    .append(line.pizza().isVegetarian() ? ", vegetarian" : "").append('\n');
        }
        String rate = taxRate.movePointRight(2).stripTrailingZeros().toPlainString();
        out.append(String.format("%-63s %9s%n", "Subtotal", subtotal()));
        out.append(String.format("%-63s %9s%n", "Tax (" + rate + "%)", tax()));
        out.append(String.format("%-63s %9s%n", "Total (" + pizzaCount() + " pizza" + (pizzaCount() == 1 ? "" : "s") + ")", total()));
        return out.toString();
    }
}
