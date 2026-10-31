package dev.omar.pizza.store;

import java.util.List;
import java.util.Locale;

/** Where an order is placed. Each region maps to one store and so one ingredient family. */
public enum Region {
    NEW_YORK("ny", "nyc", "new-york"),
    CHICAGO("chi", "chicago"),
    NAPLES("naples", "napoli", "neapolitan");

    private final List<String> aliases;

    Region(String... aliases) {
        this.aliases = List.of(aliases);
    }

    /** Accepts the enum name or any alias, case-insensitively. */
    public static Region parse(String text) {
        String key = text.trim().toLowerCase(Locale.ROOT);
        for (Region region : values()) {
            if (region.name().equalsIgnoreCase(key) || region.aliases.contains(key)) {
                return region;
            }
        }
        throw new IllegalArgumentException("Unknown region '" + text + "'. Expected ny, chicago or naples.");
    }
}
