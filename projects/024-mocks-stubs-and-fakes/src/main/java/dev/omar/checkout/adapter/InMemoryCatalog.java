package dev.omar.checkout.adapter;

import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Sku;
import dev.omar.checkout.port.Catalog;
import java.util.Map;
import java.util.Optional;

/** A fixed price list. Used by the demo; production would read from a product database. */
public final class InMemoryCatalog implements Catalog {

    private final Map<Sku, Money> prices;

    public InMemoryCatalog(Map<Sku, Money> prices) {
        this.prices = Map.copyOf(prices);
    }

    @Override
    public Optional<Money> priceOf(Sku sku) {
        return Optional.ofNullable(prices.get(sku));
    }
}
