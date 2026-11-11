package dev.omar.supportdesk;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static dev.omar.supportdesk.Tickets.FIXED_CLOCK;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** End-to-end: real config, real CSV, real chain; only the clock and the streams are substituted. */
class SupportDeskCliTest {

    private final ByteArrayOutputStream out = new ByteArrayOutputStream();
    private final ByteArrayOutputStream err = new ByteArrayOutputStream();

    private int run(String... args) {
        SupportDeskCli cli = new SupportDeskCli(
                new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8),
                FIXED_CLOCK);
        return cli.run(args);
    }

    private String stdout() {
        return out.toString(StandardCharsets.UTF_8);
    }

    private String stderr() {
        return err.toString(StandardCharsets.UTF_8);
    }

    @Test
    void routesBundledSampleThroughEveryKindOfHandler() {
        assertEquals(0, run());
        String output = stdout();
        assertTrue(output.contains("Chain: spam -> faq -> tier1 -> tier2 -> engineering"));
        assertTrue(output.contains("Summary: 10 tickets, REJECTED=1, AUTO_RESOLVED=2, ASSIGNED=5, ESCALATED=2"), output);
        // Tier 1 has capacity 3, so the fourth eligible ticket overflows to Tier 2.
        assertTrue(output.contains("T-107    ASSIGNED       tier2"), output);
        assertFalse(output.contains("Audit trail"));
    }

    @Test
    void auditFlagPrintsEveryHop() {
        assertEquals(0, run("--audit"));
        assertTrue(stdout().contains("2026-11-11T09:00:00Z  T-107    tier1          PASSED    queue full (3/3)"), stdout());
    }

    @Test
    void usesCustomConfigAndTicketFiles(@TempDir Path dir) throws IOException {
        Path config = Files.writeString(dir.resolve("c.properties"), "chain = e\ne.type = engineering-escalation\n");
        Path tickets = Files.writeString(dir.resolve("t.csv"),
                "id,customer,category,severity,subject,body\nX-1,a@b.c,OTHER,LOW,Hi,\n");

        assertEquals(0, run("--config=" + config, tickets.toString()));
        assertTrue(stdout().contains("X-1      ESCALATED      e"), stdout());
    }

    @Test
    void badOptionIsAUsageError() {
        assertEquals(1, run("--verbose"));
        assertTrue(stderr().contains("unknown option: --verbose"));
        assertTrue(stderr().contains("usage:"));
    }

    @Test
    void badConfigExitsWithCode2(@TempDir Path dir) throws IOException {
        Path config = Files.writeString(dir.resolve("c.properties"), "chain = x\nx.type = nope\n");
        assertEquals(2, run("--config=" + config));
        assertTrue(stderr().startsWith("config error: unknown handler type 'nope'"), stderr());
    }

    @Test
    void badTicketFileExitsWithCode2(@TempDir Path dir) throws IOException {
        Path tickets = Files.writeString(dir.resolve("t.csv"), "nonsense\n");
        assertEquals(2, run(tickets.toString()));
        assertTrue(stderr().startsWith("ticket file error: line 1"), stderr());
    }

    @Test
    void helpPrintsUsage() {
        assertEquals(0, run("--help"));
        assertTrue(stdout().startsWith("usage:"));
    }
}
