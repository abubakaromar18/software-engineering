package dev.omar.supportdesk.config;

import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.handlers.AgentTier;
import dev.omar.supportdesk.handlers.EngineeringEscalation;
import dev.omar.supportdesk.handlers.FaqBot;
import dev.omar.supportdesk.handlers.SpamFilter;

import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/**
 * Maps handler <em>type</em> names used in configuration ({@code tier1.type = agent-tier}) to factories.
 *
 * <p>This is the only place that knows the concrete handler classes. Adding a new kind of handler means
 * writing the class and registering one factory; the chain, the config format and the other handlers
 * are untouched (Open/Closed Principle).
 */
public final class HandlerRegistry {

    private final Map<String, HandlerFactory> factories = new TreeMap<>();

    /** A registry with the four built-in handler types. */
    public static HandlerRegistry withDefaults() {
        return new HandlerRegistry()
                .register("spam-filter", s -> new SpamFilter(s.name(), s.list("blocked-phrases")))
                .register("faq-bot", s -> new FaqBot(s.name(), s.severity("max-severity", Severity.LOW), s.group("answer")))
                .register("agent-tier", s -> new AgentTier(
                        s.name(),
                        s.string("display-name", s.name()),
                        s.categories("categories"),
                        s.severity("max-severity", Severity.MEDIUM),
                        s.integer("capacity", AgentTier.UNLIMITED)))
                .register("engineering-escalation", s -> new EngineeringEscalation(
                        s.name(), s.severity("page-at", Severity.CRITICAL)));
    }

    public HandlerRegistry register(String type, HandlerFactory factory) {
        Objects.requireNonNull(factory, "factory");
        if (factories.putIfAbsent(type, factory) != null) {
            throw new IllegalArgumentException("handler type already registered: " + type);
        }
        return this;
    }

    public HandlerFactory factoryFor(String type) {
        HandlerFactory factory = factories.get(type);
        if (factory == null) {
            throw new ConfigException("unknown handler type '" + type + "' (known: " + String.join(", ", factories.keySet()) + ")");
        }
        return factory;
    }
}
