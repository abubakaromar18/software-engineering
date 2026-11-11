package dev.omar.supportdesk.handlers;

import dev.omar.supportdesk.chain.Decision;
import dev.omar.supportdesk.chain.SupportHandler;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Answers common questions from a keyword → answer knowledge base.
 *
 * <p>Only low-severity tickets are eligible: a customer reporting an outage should talk to a person,
 * even if their message happens to mention "password".
 */
public final class FaqBot implements SupportHandler {

    private final String name;
    private final Severity maxSeverity;
    private final Map<String, String> answers;

    /** @param answers keyword → answer; iteration order decides which answer wins when several match */
    public FaqBot(String name, Severity maxSeverity, Map<String, String> answers) {
        this.name = name;
        this.maxSeverity = maxSeverity;
        Map<String, String> normalised = new LinkedHashMap<>();
        answers.forEach((keyword, answer) -> normalised.put(keyword.strip().toLowerCase(Locale.ROOT), answer.strip()));
        // Map.copyOf would lose the ordering, so wrap the ordered copy instead.
        this.answers = Collections.unmodifiableMap(normalised);
    }

    @Override
    public String name() {
        return name;
    }

    @Override
    public Decision handle(Ticket ticket) {
        if (!ticket.severity().atMost(maxSeverity)) {
            return Decision.pass("severity " + ticket.severity() + " above bot limit " + maxSeverity);
        }
        String text = ticket.searchableText();
        for (Map.Entry<String, String> faq : answers.entrySet()) {
            if (text.contains(faq.getKey())) {
                return Decision.handled(Outcome.AUTO_RESOLVED, faq.getValue());
            }
        }
        return Decision.pass("no FAQ match");
    }
}
