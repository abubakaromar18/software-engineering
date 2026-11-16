package dev.omar.checkout.doubles;

import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Sku;
import dev.omar.checkout.port.Catalog;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/** STUB — answers queries with canned data and records nothing. Tests assert on the SUT's output. */
public final class StubCatalog implements Catalog {

    private final Map<Sku, Money> prices = new HashMap<>();

    public StubCatalog price(Sku sku, Money price) {
        prices.put(sku, price);
        return this;
    }

    @Override
    public Optional<Money> priceOf(Sku sku) {
        return Optional.ofNullable(prices.get(sku));
    }
}
