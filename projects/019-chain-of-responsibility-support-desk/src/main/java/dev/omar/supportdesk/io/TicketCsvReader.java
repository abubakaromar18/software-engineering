package dev.omar.supportdesk.io;

import dev.omar.supportdesk.domain.Category;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Reads tickets from CSV with the header {@code id,customer,category,severity,subject,body}.
 *
 * <p>Supports the usual quoting rules (fields in double quotes may contain commas; {@code ""} is a
 * literal quote) but not multi-line fields, which keeps line numbers in error messages exact.
 * Blank lines and lines starting with {@code #} are skipped.
 */
public final class TicketCsvReader {

    static final List<String> HEADER = List.of("id", "customer", "category", "severity", "subject", "body");

    public List<Ticket> read(Reader source) throws IOException {
        BufferedReader reader = new BufferedReader(source);
        List<Ticket> tickets = new ArrayList<>();
        String line;
        int lineNo = 0;
        boolean headerSeen = false;
        while ((line = reader.readLine()) != null) {
            lineNo++;
            if (line.isBlank() || line.stripLeading().startsWith("#")) {
                continue;
            }
            List<String> fields = split(line, lineNo);
            if (!headerSeen) {
                checkHeader(fields, lineNo);
                headerSeen = true;
                continue;
            }
            tickets.add(toTicket(fields, lineNo));
        }
        if (!headerSeen) {
            throw new TicketParseException(lineNo, "missing header row " + String.join(",", HEADER));
        }
        return tickets;
    }

    private static void checkHeader(List<String> fields, int lineNo) {
        List<String> normalised = fields.stream().map(f -> f.strip().toLowerCase(Locale.ROOT)).toList();
        if (!normalised.equals(HEADER)) {
            throw new TicketParseException(lineNo, "expected header " + String.join(",", HEADER) + " but got " + String.join(",", fields));
        }
    }

    private static Ticket toTicket(List<String> fields, int lineNo) {
        if (fields.size() != HEADER.size()) {
            throw new TicketParseException(lineNo, "expected " + HEADER.size() + " fields, got " + fields.size());
        }
        try {
            return new Ticket(fields.get(0), fields.get(1), Category.parse(fields.get(2)),
                    Severity.parse(fields.get(3)), fields.get(4), fields.get(5));
        } catch (IllegalArgumentException e) {
            throw new TicketParseException(lineNo, e.getMessage());
        }
    }

    /** Split one CSV line into fields, honouring double-quote escaping. */
    static List<String> split(String line, int lineNo) {
        List<String> fields = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (quoted) {
                if (c == '"' && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    current.append('"');
                    i++;
                } else if (c == '"') {
                    quoted = false;
                } else {
                    current.append(c);
                }
            } else if (c == '"') {
                quoted = true;
            } else if (c == ',') {
                fields.add(current.toString());
                current.setLength(0);
            } else {
                current.append(c);
            }
        }
        if (quoted) {
            throw new TicketParseException(lineNo, "unterminated quoted field");
        }
        fields.add(current.toString());
        return fields;
    }
}
