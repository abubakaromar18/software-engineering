package dev.omar.pizza;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PizzaShopCliTest {

    private final ByteArrayOutputStream out = new ByteArrayOutputStream();
    private final ByteArrayOutputStream err = new ByteArrayOutputStream();

    private int run(Map<String, String> env, String... args) {
        return PizzaShopCli.run(args, env,
                new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8));
    }

    private String stdout() {
        return out.toString(StandardCharsets.UTF_8);
    }

    private String stderr() {
        return err.toString(StandardCharsets.UTF_8);
    }

    @Test
    void printsAReceiptForAValidOrder() {
        int code = run(Map.of(), "--region=chicago", "2:pepperoni/large");
        assertEquals(PizzaShopCli.OK, code, stderr());
        assertTrue(stdout().contains("Lakeshore Deep Dish (Chicago)"));
        assertTrue(stdout().contains("Total (2 pizzas)"));
    }

    @Test
    void defaultsToNewYork() {
        assertEquals(PizzaShopCli.OK, run(Map.of(), "cheese/s"));
        assertTrue(stdout().startsWith("Brooklyn Slice Co."));
    }

    @Test
    void honoursTheTaxRateFromTheEnvironment() {
        assertEquals(PizzaShopCli.OK, run(Map.of("PIZZA_TAX_RATE", "0"), "cheese/s"));
        assertTrue(stdout().contains("Tax (0%)"), stdout());
    }

    @Test
    void usageErrorsExitWithTwo() {
        assertEquals(PizzaShopCli.USAGE, run(Map.of()));
        assertEquals(PizzaShopCli.USAGE, run(Map.of(), "--region=mars", "cheese/s"));
        assertTrue(stderr().contains("Unknown region 'mars'"));
    }

    @Test
    void rejectedOrdersExitWithOneAndListEveryViolation() {
        int code = run(Map.of(), "pepperoni/l/+pepperoni+pepperoni");
        assertEquals(PizzaShopCli.REJECTED, code);
        assertTrue(stderr().contains("Pepperoni added 3 times"), stderr());
        assertEquals("", stdout());
    }

    @Test
    void storeRestrictionsAreReported() {
        assertEquals(PizzaShopCli.REJECTED, run(Map.of(), "--region=naples", "cheese/large"));
        assertTrue(stderr().contains("does not bake large pizzas"), stderr());
    }

    @Test
    void helpPrintsUsage() {
        assertEquals(PizzaShopCli.OK, run(Map.of(), "--help"));
        assertTrue(stdout().startsWith("Usage:"));
    }
}
