package dev.omar.supportdesk.config;

import dev.omar.supportdesk.domain.Category;
import dev.omar.supportdesk.domain.Severity;

import java.util.Arrays;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Function;

/**
 * Typed, read-only view of one handler's settings: the properties under {@code <name>.}.
 *
 * <p>Every read is remembered so that {@link #unusedKeys()} can report keys nobody asked for. That
 * turns a typo such as {@code tier1.capacty = 3} into a startup error instead of a silently ignored
 * setting.
 */
public final class HandlerSettings {

    private final String name;
    private final Properties properties;
    private final Set<String> readKeys = new HashSet<>();

    public HandlerSettings(String name, Properties properties) {
        this.name = name;
        this.properties = properties;
    }

    /** The handler instance name, as listed in {@code chain}. */
    public String name() {
        return name;
    }

    public String string(String key) {
        String value = raw(key);
        if (value == null || value.isBlank()) {
            throw new ConfigException("missing required setting '" + fullKey(key) + "'");
        }
        return value.strip();
    }

    public String string(String key, String defaultValue) {
        String value = raw(key);
        return value == null || value.isBlank() ? defaultValue : value.strip();
    }

    /** Comma-separated list; empty when the key is absent. */
    public List<String> list(String key) {
        String value = raw(key);
        if (value == null) {
            return List.of();
        }
        return Arrays.stream(value.split(",")).map(String::strip).filter(s -> !s.isEmpty()).toList();
    }

    public int integer(String key, int defaultValue) {
        String value = raw(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        try {
            return Integer.parseInt(value.strip());
        } catch (NumberFormatException e) {
            throw new ConfigException("'" + fullKey(key) + "' must be an integer, got '" + value.strip() + "'", e);
        }
    }

    public Severity severity(String key, Severity defaultValue) {
        String value = raw(key);
        return value == null || value.isBlank() ? defaultValue : parse(key, value, Severity::parse);
    }

    /** Comma-separated categories; at least one is required. */
    public Set<Category> categories(String key) {
        List<String> values = list(key);
        if (values.isEmpty()) {
            throw new ConfigException("missing required setting '" + fullKey(key) + "'");
        }
        Set<Category> result = EnumSet.noneOf(Category.class);
        values.forEach(v -> result.add(parse(key, v, Category::parse)));
        return result;
    }

    /**
     * All settings under {@code <name>.<prefix>.}, keyed by the remainder. {@link Properties} does not
     * keep file order, so entries are returned sorted by key to stay deterministic.
     */
    public Map<String, String> group(String prefix) {
        String start = fullKey(prefix) + ".";
        Map<String, String> result = new LinkedHashMap<>();
        new TreeSet<>(properties.stringPropertyNames()).stream()
                .filter(k -> k.startsWith(start))
                .forEach(k -> {
                    readKeys.add(k);
                    result.put(k.substring(start.length()), properties.getProperty(k));
                });
        return result;
    }

    /** Keys under this handler's prefix that were never read, sorted. */
    public Set<String> unusedKeys() {
        String start = name + ".";
        Set<String> unused = new TreeSet<>();
        for (String key : properties.stringPropertyNames()) {
            if (key.startsWith(start) && !readKeys.contains(key)) {
                unused.add(key);
            }
        }
        return unused;
    }

    private String raw(String key) {
        String full = fullKey(key);
        readKeys.add(full);
        return properties.getProperty(full);
    }

    private String fullKey(String key) {
        return name + "." + key;
    }

    private <T> T parse(String key, String value, Function<String, T> parser) {
        try {
            return parser.apply(value);
        } catch (IllegalArgumentException e) {
            throw new ConfigException("'" + fullKey(key) + "': " + e.getMessage(), e);
        }
    }
}
