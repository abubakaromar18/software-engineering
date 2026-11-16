package dev.omar.checkout;

import dev.omar.checkout.adapter.ConsoleNotifier;
import dev.omar.checkout.adapter.InMemoryCatalog;
import dev.omar.checkout.adapter.InMemoryInventory;
import dev.omar.checkout.adapter.InMemoryOrderRepository;
import dev.omar.checkout.adapter.SequentialOrderIdGenerator;
import dev.omar.checkout.adapter.SimulatedPaymentGateway;
import dev.omar.checkout.domain.CheckoutRequest;
import dev.omar.checkout.domain.CheckoutResult;
import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Sku;
import dev.omar.checkout.service.CheckoutService;
import java.io.PrintStream;
import java.time.Clock;
import java.util.List;
import java.util.Map;

/**
 * Composition root: wires the service to in-memory fakes and runs a few scripted checkouts.
 * The same fakes the tests rely on make the whole app runnable with zero infrastructure.
 */
public final class CheckoutDemo {

    private CheckoutDemo() {
    }

    public static void main(String[] args) {
        run(System.out, Clock.systemUTC());
    }

    static void run(PrintStream out, Clock clock) {
        Sku book = new Sku("BOOK-042");
        Sku mug = new Sku("MUG-001");
        Sku poster = new Sku("POSTER-7");
        InMemoryInventory inventory = new InMemoryInventory(Map.of(book, 5, mug, 1, poster, 3));
        SimulatedPaymentGateway payments = new SimulatedPaymentGateway(Money.ofCents(100_00));
        CheckoutService service = new CheckoutService(
                new InMemoryCatalog(Map.of(book, Money.ofCents(24_99), mug, Money.ofCents(12_50), poster, Money.ofCents(45_00))),
                inventory, payments, new InMemoryOrderRepository(), new ConsoleNotifier(out),
                new SequentialOrderIdGenerator("ORD"), clock);

        CustomerId ada = new CustomerId("ada");
        List<CheckoutRequest> script = List.of(
                new CheckoutRequest(ada, List.of(item(book, 2), item(mug, 1))),
                new CheckoutRequest(ada, List.of(item(mug, 1))),
                new CheckoutRequest(ada, List.of(item(poster, 3))),
                new CheckoutRequest(ada, List.of(item(new Sku("GADGET-9"), 1))),
                new CheckoutRequest(ada, List.of()));

        for (CheckoutRequest request : script) {
            out.println("checkout " + describe(request));
            switch (service.placeOrder(request)) {
                case CheckoutResult.Placed placed ->
                        out.printf("  placed %s for %s%n", placed.order().id(), placed.order().total());
                case CheckoutResult.Rejected rejected ->
                        out.printf("  rejected: %s (%s)%n", rejected.reason(), rejected.detail());
            }
        }
        out.printf("orders for %s: %d | gateway balance %s | %s left in stock: %d%n",
                ada, service.orderHistory(ada).size(), payments.balance(), mug, inventory.available(mug));
    }

    private static CheckoutRequest.Item item(Sku sku, int quantity) {
        return new CheckoutRequest.Item(sku, quantity);
    }

    private static String describe(CheckoutRequest request) {
        if (request.items().isEmpty()) {
            return "(empty cart)";
        }
        return String.join(", ", request.items().stream().map(i -> i.quantity() + "x " + i.sku()).toList());
    }
}
