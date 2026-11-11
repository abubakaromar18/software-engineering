package dev.omar.supportdesk.io;

import dev.omar.supportdesk.domain.Category;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.StringReader;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TicketCsvReaderTest {

    private static final String HEADER = "id,customer,category,severity,subject,body\n";

    private final TicketCsvReader reader = new TicketCsvReader();

    private List<Ticket> read(String csv) throws IOException {
        return reader.read(new StringReader(csv));
    }

    @Test
    void readsTicketsWithQuotedCommasAndEscapedQuotes() throws IOException {
        List<Ticket> tickets = read(HEADER + "T-1,a@example.com,billing,low,\"Refund, please\",\"She said \"\"soon\"\"\"\n");
        assertEquals(List.of(new Ticket("T-1", "a@example.com", Category.BILLING, Severity.LOW,
                "Refund, please", "She said \"soon\"")), tickets);
    }

    @Test
    void skipsBlankLinesAndComments() throws IOException {
        List<Ticket> tickets = read("# exported 2026-11-11\n\n" + HEADER + "\nT-1,a,ACCOUNT,LOW,Hi,\n# end\n");
        assertEquals(1, tickets.size());
        assertEquals("", tickets.get(0).body());
    }

    @Test
    void headerIsCaseInsensitive() throws IOException {
        assertEquals(0, read("ID,Customer,Category,Severity,Subject,Body\n").size());
    }

    @Test
    void rejectsWrongHeader() {
        TicketParseException e = assertThrows(TicketParseException.class, () -> read("id,who,what\n"));
        assertEquals(1, e.line());
    }

    @Test
    void rejectsEmptyInput() {
        assertThrows(TicketParseException.class, () -> read(""));
    }

    @Test
    void reportsLineNumberOfWrongFieldCount() {
        TicketParseException e = assertThrows(TicketParseException.class,
                () -> read(HEADER + "T-1,a,ACCOUNT,LOW,Hi,\nT-2,b,ACCOUNT\n"));
        assertEquals(3, e.line());
        assertTrue(e.getMessage().contains("expected 6 fields, got 3"));
    }

    @Test
    void reportsLineNumberOfInvalidValues() {
        TicketParseException e = assertThrows(TicketParseException.class,
                () -> read(HEADER + "T-1,a,ACCOUNT,URGENT,Hi,\n"));
        assertEquals("line 2: unknown severity 'URGENT' (expected one of LOW, MEDIUM, HIGH, CRITICAL)", e.getMessage());

        TicketParseException blank = assertThrows(TicketParseException.class,
                () -> read(HEADER + "T-1,a,ACCOUNT,LOW, ,\n"));
        assertTrue(blank.getMessage().contains("subject must not be blank"));
    }

    @Test
    void rejectsUnterminatedQuote() {
        TicketParseException e = assertThrows(TicketParseException.class,
                () -> read(HEADER + "T-1,a,ACCOUNT,LOW,\"Hi,\n"));
        assertTrue(e.getMessage().contains("unterminated"));
    }
}
