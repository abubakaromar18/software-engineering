package dev.omar.pizza.store;

/**
 * <b>Simple (static) factory.</b> Not one of the Gang of Four patterns, but the most common
 * factory in real code: one method that maps a key to a concrete class. It is the only place in
 * the program that names a concrete store, so adding a region touches this switch and nothing
 * else. Because {@link Region} is an enum, the compiler flags a missing case.
 */
public final class PizzaStores {

    private PizzaStores() {
    }

    public static PizzaStore forRegion(Region region) {
        return switch (region) {
            case NEW_YORK -> new NewYorkPizzaStore();
            case CHICAGO -> new ChicagoPizzaStore();
            case NAPLES -> new NeapolitanPizzaStore();
        };
    }
}
