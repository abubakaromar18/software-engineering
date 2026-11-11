package dev.omar.supportdesk.audit;

/** What happened at one hop of a ticket's journey through the chain. */
public enum AuditStep {
    /** The handler declined the ticket and gave a reason. */
    PASSED,
    /** The handler accepted the ticket; this is the last entry for that ticket. */
    HANDLED,
    /** The handler threw; the chain logged the error and carried on to the next handler. */
    FAILED,
    /** The end of the chain was reached without anyone accepting the ticket. */
    UNHANDLED
}
