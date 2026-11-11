package dev.omar.supportdesk.config;

import dev.omar.supportdesk.audit.InMemoryAuditTrail;
import dev.omar.supportdesk.chain.Decision;
import dev.omar.supportdesk.chain.SupportChain;
import dev.omar.supportdesk.chain.SupportHandler;
import dev.omar.supportdesk.domain.Category;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Resolution;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.io.StringReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Properties;

import static dev.omar.supportdesk.Tickets.FIXED_CLOCK;
import static dev.omar.supportdesk.Tickets.ticket;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ChainFactoryTest {

    private final ChainFactory factory = new ChainFactory(HandlerRegistry.withDefaults(), new InMemoryAuditTrail(), FIXED_CLOCK);

    private static Properties props(String text) {
        Properties p = new Properties();
        try {
            p.load(new StringReader(text));
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
        return p;
    }

    private void assertConfigError(String config, String expectedFragment) {
        ConfigException e = assertThrows(ConfigException.class, () -> factory.build(props(config)));
        assertTrue(e.getMessage().contains(expectedFragment),
                () -> "expected message containing '" + expectedFragment + "' but was: " + e.getMessage());
    }

    @Test
    void bundledDefaultConfigBuildsTheDocumentedChain() {
        SupportChain chain = factory.buildDefault();
        assertEquals(List.of("spam", "faq", "tier1", "tier2", "engineering"), chain.handlerNames());
    }

    @Test
    void reorderingIsPureConfiguration() {
        // Same handler types, different order: engineering first swallows everything.
        SupportChain chain = factory.build(props("""
                chain = engineering, tier1
                engineering.type = engineering-escalation
                tier1.type = agent-tier
                tier1.categories = ACCOUNT
                """));
        Resolution r = chain.process(ticket(Category.ACCOUNT, Severity.LOW));
        assertEquals("engineering", r.handledBy());
    }

    @Test
    void sameTypeCanBeConfiguredTwiceUnderDifferentNames() {
        SupportChain chain = factory.build(props("""
                chain = tier1, tier2
                tier1.type = agent-tier
                tier1.categories = BILLING
                tier1.capacity = 1
                tier2.type = agent-tier
                tier2.categories = BILLING
                """));
        Ticket t = ticket(Category.BILLING, Severity.LOW);
        assertEquals("tier1", chain.process(t).handledBy());
        assertEquals("tier2", chain.process(t).handledBy());
    }

    @Test
    void newHandlerTypesPlugInThroughTheRegistry() {
        HandlerRegistry registry = HandlerRegistry.withDefaults().register("vip-concierge", s -> new SupportHandler() {
            private final String domain = s.string("domain");

            @Override
            public String name() {
                return s.name();
            }

            @Override
            public Decision handle(Ticket ticket) {
                return ticket.customer().endsWith("@" + domain)
                        ? Decision.handled(Outcome.ASSIGNED, "VIP concierge")
                        : Decision.pass("not a VIP");
            }
        });
        SupportChain chain = new ChainFactory(registry, new InMemoryAuditTrail(), FIXED_CLOCK).build(props("""
                chain = vip
                vip.type = vip-concierge
                vip.domain = example.com
                """));
        assertEquals("VIP concierge", chain.process(ticket(Category.OTHER, Severity.LOW)).message());
    }

    @Test
    void failsOnMissingChain() {
        assertConfigError("spam.type = spam-filter", "missing required setting 'chain'");
    }

    @Test
    void failsOnUnknownType() {
        assertConfigError("chain = x\nx.type = carrier-pigeon", "unknown handler type 'carrier-pigeon'");
    }

    @Test
    void failsOnMissingType() {
        assertConfigError("chain = x", "missing required setting 'x.type'");
    }

    @Test
    void failsOnMisspeltSettingInsteadOfIgnoringIt() {
        assertConfigError("""
                chain = tier1
                tier1.type = agent-tier
                tier1.categories = ACCOUNT
                tier1.capacty = 3
                """, "unknown setting(s) for handler 'tier1': tier1.capacty");
    }

    @Test
    void failsOnMalformedValuesNamingTheKey() {
        assertConfigError("chain = t\nt.type = agent-tier\nt.categories = ACCOUNT\nt.capacity = lots",
                "'t.capacity' must be an integer");
        assertConfigError("chain = t\nt.type = agent-tier\nt.categories = ACCOUNT\nt.max-severity = URGENT",
                "'t.max-severity': unknown severity 'URGENT'");
        assertConfigError("chain = t\nt.type = agent-tier\nt.categories = SALES",
                "'t.categories': unknown category 'SALES'");
    }

    @Test
    void turnsConstructorValidationIntoConfigErrors() {
        assertConfigError("chain = t\nt.type = agent-tier\nt.categories = ACCOUNT\nt.capacity = -1",
                "capacity must be >= 0");
    }

    @Test
    void failsOnDuplicateNamesInChain() {
        assertConfigError("chain = e, e\ne.type = engineering-escalation", "duplicate handler name");
    }

    @Test
    void readsConfigFromFileAndReportsMissingFile(@TempDir Path dir) throws IOException {
        Path file = dir.resolve("desk.properties");
        Files.writeString(file, "chain = e\ne.type = engineering-escalation\n");
        assertEquals(List.of("e"), factory.build(file).handlerNames());

        ConfigException e = assertThrows(ConfigException.class, () -> factory.build(dir.resolve("nope.properties")));
        assertTrue(e.getMessage().startsWith("cannot read config file"));
    }
}
