package dev.omar.supportdesk.io;

import java.io.Serial;

/** A ticket file could not be parsed. Carries the 1-based line number of the problem. */
public final class TicketParseException extends RuntimeException {

    @Serial
    private static final long serialVersionUID = 1L;

    private final int line;

    public TicketParseException(int line, String message) {
        super("line " + line + ": " + message);
        this.line = line;
    }

    public int line() {
        return line;
    }
}
