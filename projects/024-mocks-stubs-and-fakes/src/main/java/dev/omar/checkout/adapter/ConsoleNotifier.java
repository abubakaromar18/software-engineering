package dev.omar.checkout.adapter;

import dev.omar.checkout.domain.Order;
import dev.omar.checkout.port.Notifier;
import java.io.PrintStream;
import java.util.Objects;

/** Writes confirmations to a stream instead of sending email. */
public final class ConsoleNotifier implements Notifier {

    private final PrintStream out;

    public ConsoleNotifier(PrintStream out) {
        this.out = Objects.requireNonNull(out, "out");
    }

    @Override
    public void orderConfirmed(Order order) {
        out.printf("  [email to %s] order %s confirmed, total %s%n", order.customer(), order.id(), order.total());
    }
}
