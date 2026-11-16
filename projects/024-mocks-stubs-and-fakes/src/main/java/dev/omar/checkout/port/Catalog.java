package dev.omar.checkout.port;

import dev.omar.checkout.domain.Money;
import dev.omar.checkout.domain.Sku;
import java.util.Optional;

/** Read-only source of current prices. A query port: tests usually replace it with a stub. */
public interface Catalog {

    /** The current unit price, or empty if the SKU is not sold. */
    Optional<Money> priceOf(Sku sku);
}
