package dev.omar.supportdesk;

import dev.omar.supportdesk.audit.AuditEntry;
import dev.omar.supportdesk.audit.InMemoryAuditTrail;
import dev.omar.supportdesk.chain.SupportChain;
import dev.omar.supportdesk.config.ChainFactory;
import dev.omar.supportdesk.config.ConfigException;
import dev.omar.supportdesk.config.HandlerRegistry;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Resolution;
import dev.omar.supportdesk.domain.Ticket;
import dev.omar.supportdesk.io.TicketCsvReader;
import dev.omar.supportdesk.io.TicketParseException;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * Command-line entry point and composition root: the only class that wires config, chain, audit
 * trail and I/O together.
 *
 * <pre>
 * java -jar support-desk.jar [--config=FILE] [--audit] [TICKETS.csv]
 * </pre>
 *
 * Exit codes: 0 success, 1 usage error, 2 bad configuration or ticket file.
 */
public final class SupportDeskCli {

    static final String SAMPLE_TICKETS = "/sample-tickets.csv";
    static final String USAGE = "usage: support-desk [--config=FILE] [--audit] [TICKETS.csv]";

    private final PrintStream out;
    private final PrintStream err;
    private final Clock clock;

    SupportDeskCli(PrintStream out, PrintStream err, Clock clock) {
        this.out = out;
        this.err = err;
        this.clock = clock;
    }

    public static void main(String[] args) {
        System.exit(new SupportDeskCli(System.out, System.err, Clock.systemUTC()).run(args));
    }

    int run(String[] args) {
        Options options;
        try {
            options = Options.parse(args);
        } catch (IllegalArgumentException e) {
            err.println(e.getMessage());
            err.println(USAGE);
            return 1;
        }
        if (options.help()) {
            out.println(USAGE);
            return 0;
        }
        try {
            InMemoryAuditTrail audit = new InMemoryAuditTrail();
            ChainFactory factory = new ChainFactory(HandlerRegistry.withDefaults(), audit, clock);
            SupportChain chain = options.config() == null ? factory.buildDefault() : factory.build(options.config());
            List<Resolution> resolutions = chain.processAll(readTickets(options.tickets()));

            out.println("Chain: " + String.join(" -> ", chain.handlerNames()));
            out.println();
            printResolutions(resolutions);
            if (options.audit()) {
                out.println();
                out.println("Audit trail:");
                audit.entries().stream().map(AuditEntry::format).forEach(line -> out.println("  " + line));
            }
            return 0;
        } catch (ConfigException e) {
            err.println("config error: " + e.getMessage());
            return 2;
        } catch (TicketParseException e) {
            err.println("ticket file error: " + e.getMessage());
            return 2;
        } catch (IOException e) {
            err.println("cannot read tickets: " + e.getMessage());
            return 2;
        }
    }

    private List<Ticket> readTickets(Path file) throws IOException {
        TicketCsvReader reader = new TicketCsvReader();
        if (file != null) {
            try (Reader in = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
                return reader.read(in);
            }
        }
        InputStream sample = SupportDeskCli.class.getResourceAsStream(SAMPLE_TICKETS);
        if (sample == null) {
            throw new IOException("bundled sample " + SAMPLE_TICKETS + " not found on classpath");
        }
        try (Reader in = new InputStreamReader(sample, StandardCharsets.UTF_8)) {
            return reader.read(in);
        }
    }

    private void printResolutions(List<Resolution> resolutions) {
        out.printf("%-8s %-14s %-14s %s%n", "TICKET", "OUTCOME", "HANDLED BY", "MESSAGE");
        Map<Outcome, Integer> counts = new EnumMap<>(Outcome.class);
        for (Resolution r : resolutions) {
            out.printf("%-8s %-14s %-14s %s%n", r.ticketId(), r.outcome(), r.handledBy(), r.message());
            counts.merge(r.outcome(), 1, Integer::sum);
        }
        out.println();
        StringBuilder summary = new StringBuilder("Summary: " + resolutions.size() + " tickets");
        counts.forEach((outcome, n) -> summary.append(", ").append(outcome).append('=').append(n));
        out.println(summary);
    }

    /** Parsed command-line options. {@code null} paths mean "use the bundled default". */
    record Options(Path config, Path tickets, boolean audit, boolean help) {

        static Options parse(String[] args) {
            Path config = null;
            Path tickets = null;
            boolean audit = false;
            boolean help = false;
            for (String arg : args) {
                if (arg.equals("--audit")) {
                    audit = true;
                } else if (arg.equals("--help") || arg.equals("-h")) {
                    help = true;
                } else if (arg.startsWith("--config=")) {
                    config = Path.of(arg.substring("--config=".length()));
                } else if (arg.startsWith("-")) {
                    throw new IllegalArgumentException("unknown option: " + arg);
                } else if (tickets == null) {
                    tickets = Path.of(arg);
                } else {
                    throw new IllegalArgumentException("only one tickets file may be given");
                }
            }
            return new Options(config, tickets, audit, help);
        }
    }
}
