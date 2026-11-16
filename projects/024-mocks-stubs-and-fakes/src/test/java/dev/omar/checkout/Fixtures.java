package dev.omar.checkout;

import dev.omar.checkout.domain.CheckoutRequest;
import dev.omar.checkout.domain.CustomerId;
import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Sku;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Arrays;

/** Shared test data so each test reads as intent, not setup. */
public final class Fixtures {

    public static final Sku BOOK = new Sku("BOOK-1");
    public static final Sku MUG = new Sku("MUG-2");
    public static final Money BOOK_PRICE = Money.ofCents(20_00);
    public static final Money MUG_PRICE = Money.ofCents(7_50);
    public static final CustomerId ADA = new CustomerId("ada");
    public static final CustomerId GRACE = new CustomerId("grace");
    public static final Instant NOW = Instant.parse("2026-11-16T09:00:00Z");
    /** The JDK ships its own stub: a clock that always answers the same instant. */
    public static final Clock FIXED_CLOCK = Clock.fixed(NOW, ZoneOffset.UTC);

    private Fixtures() {
    }

    public static CheckoutRequest.Item item(Sku sku, int quantity) {
        return new CheckoutRequest.Item(sku, quantity);
    }

    public static CheckoutRequest cart(CustomerId customer, CheckoutRequest.Item... items) {
        return new CheckoutRequest(customer, Arrays.asList(items));
    }
}
