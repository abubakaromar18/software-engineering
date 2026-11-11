package dev.omar.supportdesk.config;

import dev.omar.supportdesk.audit.AuditTrail;
import dev.omar.supportdesk.chain.SupportChain;
import dev.omar.supportdesk.chain.SupportHandler;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.Properties;
import java.util.Set;

/**
 * Turns a properties file into a ready-to-use {@link SupportChain}.
 *
 * <pre>
 * chain = spam, faq, tier1, tier2, engineering   # order matters
 * tier1.type = agent-tier                        # which factory builds this link
 * tier1.categories = ACCOUNT, BILLING            # type-specific settings
 * </pre>
 *
 * <p>All validation happens here, at startup: unknown types, missing or malformed settings, unused
 * (probably misspelt) keys, and duplicate names all fail fast with a message that names the key.
 */
public final class ChainFactory {

    /** Classpath location of the configuration the CLI uses when no file is given. */
    public static final String DEFAULT_RESOURCE = "/support-desk.properties";

    private final HandlerRegistry registry;
    private final AuditTrail audit;
    private final Clock clock;

    public ChainFactory(HandlerRegistry registry, AuditTrail audit, Clock clock) {
        this.registry = Objects.requireNonNull(registry, "registry");
        this.audit = Objects.requireNonNull(audit, "audit");
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    public SupportChain build(Properties properties) {
        List<SupportHandler> handlers = new ArrayList<>();
        for (String name : chainNames(properties)) {
            handlers.add(buildHandler(name, properties));
        }
        try {
            return new SupportChain(handlers, audit, clock);
        } catch (IllegalArgumentException e) {
            throw new ConfigException(e.getMessage(), e);
        }
    }

    public SupportChain build(Path file) {
        try (Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            return build(load(reader));
        } catch (IOException e) {
            throw new ConfigException("cannot read config file " + file + ": " + e.getMessage(), e);
        }
    }

    public SupportChain buildDefault() {
        InputStream in = ChainFactory.class.getResourceAsStream(DEFAULT_RESOURCE);
        if (in == null) {
            throw new ConfigException("default config " + DEFAULT_RESOURCE + " not found on classpath");
        }
        try (Reader reader = new InputStreamReader(in, StandardCharsets.UTF_8)) {
            return build(load(reader));
        } catch (IOException e) {
            throw new ConfigException("cannot read default config: " + e.getMessage(), e);
        }
    }

    private static Properties load(Reader reader) throws IOException {
        Properties properties = new Properties();
        properties.load(reader);
        return properties;
    }

    private static List<String> chainNames(Properties properties) {
        String chain = properties.getProperty("chain");
        if (chain == null || chain.isBlank()) {
            throw new ConfigException("missing required setting 'chain' (comma-separated handler names)");
        }
        return Arrays.stream(chain.split(",")).map(String::strip).filter(s -> !s.isEmpty()).toList();
    }

    private SupportHandler buildHandler(String name, Properties properties) {
        HandlerSettings settings = new HandlerSettings(name, properties);
        SupportHandler handler;
        try {
            handler = registry.factoryFor(settings.string("type")).create(settings);
        } catch (ConfigException e) {
            throw e;
        } catch (IllegalArgumentException e) {
            // Constructors validate their own invariants; re-badge those as configuration errors.
            throw new ConfigException(e.getMessage(), e);
        }
        Set<String> unused = settings.unusedKeys();
        if (!unused.isEmpty()) {
            throw new ConfigException("unknown setting(s) for handler '" + name + "': " + String.join(", ", unused));
        }
        return handler;
    }
}
