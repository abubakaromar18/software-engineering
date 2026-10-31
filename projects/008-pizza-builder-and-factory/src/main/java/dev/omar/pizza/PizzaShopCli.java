package dev.omar.pizza;

import dev.omar.pizza.domain.InvalidPizzaException;
import dev.omar.pizza.order.Order;
import dev.omar.pizza.order.OrderService;
import dev.omar.pizza.order.PizzaRequest;
import dev.omar.pizza.order.ShopConfig;
import dev.omar.pizza.store.PizzaStore;
import dev.omar.pizza.store.PizzaStores;
import dev.omar.pizza.store.Region;
import dev.omar.pizza.store.UnsupportedOrderException;

import java.io.PrintStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Command-line entry point. All wiring happens here (the "composition root"): config is read,
 * the simple factory picks a store, and the order service is given that store.
 *
 * <pre>
 *   pizza [--region=ny|chicago|naples] [N:]item/size[/+topping+...] ...
 * </pre>
 */
public final class PizzaShopCli {

    static final int OK = 0;
    static final int REJECTED = 1;
    static final int USAGE = 2;

    private static final String USAGE_TEXT = """
            Usage: pizza [--region=ny|chicago|naples] [N:]item/size[/+topping+topping...] ...
              e.g. pizza --region=ny 2:pepperoni/large/+mushroom margherita/small
            Items:    cheese, margherita, pepperoni, veggie, meat-lovers, hawaiian
            Sizes:    small, medium, large (or s, m, l)
            Toppings: pepperoni, sausage, ham, mushroom, onion, green-pepper,
                      black-olive, basil, jalapeno, pineapple
            Env:      PIZZA_TAX_RATE (default 0.0825)""";

    private PizzaShopCli() {
    }

    public static void main(String[] args) {
        System.exit(run(args, System.getenv(), System.out, System.err));
    }

    /** Runs the CLI and returns the process exit code. Separated from {@code main} for testing. */
    static int run(String[] args, Map<String, String> env, PrintStream out, PrintStream err) {
        Region region = Region.NEW_YORK;
        List<PizzaRequest> requests = new ArrayList<>();
        ShopConfig config;
        try {
            config = ShopConfig.fromEnvironment(env);
            for (String arg : args) {
                if (arg.equals("-h") || arg.equals("--help")) {
                    out.println(USAGE_TEXT);
                    return OK;
                } else if (arg.startsWith("--region=")) {
                    region = Region.parse(arg.substring("--region=".length()));
                } else {
                    requests.add(PizzaRequest.parse(arg));
                }
            }
        } catch (IllegalArgumentException e) {
            err.println("error: " + e.getMessage());
            err.println(USAGE_TEXT);
            return USAGE;
        }
        if (requests.isEmpty()) {
            err.println(USAGE_TEXT);
            return USAGE;
        }

        PizzaStore store = PizzaStores.forRegion(region);
        try {
            Order order = new OrderService(store, config.taxRate()).place(requests);
            out.print(order.receipt());
            return OK;
        } catch (UnsupportedOrderException e) {
            err.println("order rejected: " + e.getMessage());
            return REJECTED;
        } catch (InvalidPizzaException e) {
            err.println("order rejected:");
            e.violations().forEach(v -> err.println("  - " + v));
            return REJECTED;
        }
    }
}
