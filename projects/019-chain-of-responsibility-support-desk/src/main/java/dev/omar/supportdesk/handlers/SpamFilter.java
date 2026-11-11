package dev.omar.supportdesk.handlers;

import dev.omar.supportdesk.chain.Decision;
import dev.omar.supportdesk.chain.SupportHandler;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Ticket;

import java.util.List;
import java.util.Locale;

/** Rejects tickets containing any blocked phrase. Belongs first in the chain so spam never reaches people. */
public final class SpamFilter implements SupportHandler {

    private final String name;
    private final List<String> blockedPhrases;

    public SpamFilter(String name, List<String> blockedPhrases) {
        this.name = name;
        this.blockedPhrases = blockedPhrases.stream()
                .map(p -> p.strip().toLowerCase(Locale.ROOT))
                .filter(p -> !p.isEmpty())
                .toList();
    }

    @Override
    public String name() {
        return name;
    }

    @Override
    public Decision handle(Ticket ticket) {
        String text = ticket.searchableText();
        return blockedPhrases.stream()
                .filter(text::contains)
                .findFirst()
                .map(phrase -> Decision.handled(Outcome.REJECTED, "blocked phrase '" + phrase + "'"))
                .orElseGet(() -> Decision.pass("no blocked phrases"));
    }
}
