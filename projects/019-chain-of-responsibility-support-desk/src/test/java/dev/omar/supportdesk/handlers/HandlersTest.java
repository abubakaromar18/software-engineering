package dev.omar.supportdesk.handlers;

import dev.omar.supportdesk.chain.Decision;
import dev.omar.supportdesk.domain.Category;
import dev.omar.supportdesk.domain.Outcome;
import dev.omar.supportdesk.domain.Severity;
import dev.omar.supportdesk.domain.Ticket;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static dev.omar.supportdesk.Tickets.ticket;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

class HandlersTest {

    @Nested
    class SpamFilterTest {

        private final SpamFilter filter = new SpamFilter("spam", List.of(" Free Money ", "", "giveaway"));

        @Test
        void rejectsBlockedPhraseCaseInsensitively() {
            Ticket spam = new Ticket("T-1", "x@example.net", Category.OTHER, Severity.LOW, "Hello", "Get FREE money now");
            assertEquals(Decision.handled(Outcome.REJECTED, "blocked phrase 'free money'"), filter.handle(spam));
        }

        @Test
        void passesCleanTicketsAndIgnoresBlankPhrases() {
            assertEquals(Decision.pass("no blocked phrases"), filter.handle(ticket(Category.ACCOUNT, Severity.LOW)));
        }
    }

    @Nested
    class FaqBotTest {

        private final FaqBot bot = new FaqBot("faq", Severity.LOW, orderedAnswers());

        private static Map<String, String> orderedAnswers() {
            Map<String, String> answers = new LinkedHashMap<>();
            answers.put("Password", "Use the reset link.");
            answers.put("invoice", "Billing > History.");
            return answers;
        }

        @Test
        void answersMatchingLowSeverityTicket() {
            Ticket t = ticket("T-1", Category.ACCOUNT, Severity.LOW, "Forgot my password");
            assertEquals(Decision.handled(Outcome.AUTO_RESOLVED, "Use the reset link."), bot.handle(t));
        }

        @Test
        void firstMatchingAnswerWinsInGivenOrder() {
            Ticket t = ticket("T-1", Category.BILLING, Severity.LOW, "password on invoice");
            assertEquals("Use the reset link.", ((Decision.Handled) bot.handle(t)).message());
        }

        @Test
        void leavesSevereTicketsToHumansEvenWhenKeywordMatches() {
            Ticket t = ticket("T-1", Category.ACCOUNT, Severity.HIGH, "password reset broken for everyone");
            assertEquals(Decision.pass("severity HIGH above bot limit LOW"), bot.handle(t));
        }

        @Test
        void passesWhenNothingMatches() {
            assertEquals(Decision.pass("no FAQ match"), bot.handle(ticket(Category.ACCOUNT, Severity.LOW)));
        }
    }

    @Nested
    class AgentTierTest {

        private AgentTier tier(int capacity) {
            return new AgentTier("tier1", "Tier 1", Set.of(Category.ACCOUNT, Category.BILLING), Severity.MEDIUM, capacity);
        }

        @Test
        void acceptsCoveredCategoryWithinSeverity() {
            assertEquals(Decision.handled(Outcome.ASSIGNED, "assigned to Tier 1 queue"),
                    tier(0).handle(ticket(Category.BILLING, Severity.MEDIUM)));
        }

        @Test
        void passesUncoveredCategory() {
            assertEquals(Decision.pass("category TECHNICAL not covered"),
                    tier(0).handle(ticket(Category.TECHNICAL, Severity.LOW)));
        }

        @Test
        void passesTooSevereTicket() {
            assertEquals(Decision.pass("severity HIGH above tier limit MEDIUM"),
                    tier(0).handle(ticket(Category.ACCOUNT, Severity.HIGH)));
        }

        @Test
        void overflowsToNextHandlerWhenQueueIsFull() {
            AgentTier tier = tier(2);
            Ticket t = ticket(Category.ACCOUNT, Severity.LOW);
            assertInstanceOf(Decision.Handled.class, tier.handle(t));
            assertInstanceOf(Decision.Handled.class, tier.handle(t));
            assertEquals(Decision.pass("queue full (2/2)"), tier.handle(t));
            assertEquals(2, tier.assignedCount());
        }

        @Test
        void unlimitedCapacityNeverFills() {
            AgentTier tier = tier(AgentTier.UNLIMITED);
            for (int i = 0; i < 1_000; i++) {
                assertInstanceOf(Decision.Handled.class, tier.handle(ticket(Category.ACCOUNT, Severity.LOW)));
            }
        }

        @Test
        void capacityHoldsUnderConcurrentLoad() throws Exception {
            AgentTier tier = tier(10);
            Ticket t = ticket(Category.ACCOUNT, Severity.LOW);
            List<Callable<Decision>> jobs = new ArrayList<>();
            for (int i = 0; i < 200; i++) {
                jobs.add(() -> tier.handle(t));
            }
            int accepted = 0;
            try (ExecutorService pool = Executors.newFixedThreadPool(16)) {
                for (Future<Decision> f : pool.invokeAll(jobs)) {
                    if (f.get() instanceof Decision.Handled) {
                        accepted++;
                    }
                }
            }
            assertEquals(10, accepted);
            assertEquals(10, tier.assignedCount());
        }

        @Test
        void rejectsInvalidConfiguration() {
            assertThrows(IllegalArgumentException.class,
                    () -> new AgentTier("t", "T", Set.of(), Severity.LOW, 0));
            assertThrows(IllegalArgumentException.class,
                    () -> new AgentTier("t", "T", Set.of(Category.ACCOUNT), Severity.LOW, -1));
        }
    }

    @Nested
    class EngineeringEscalationTest {

        private final EngineeringEscalation engineering = new EngineeringEscalation("eng", Severity.HIGH);

        @ParameterizedTest
        @EnumSource(value = Severity.class, names = {"HIGH", "CRITICAL"})
        void pagesAtOrAboveThreshold(Severity severity) {
            Decision d = engineering.handle(ticket(Category.TECHNICAL, severity));
            assertEquals(Decision.handled(Outcome.ESCALATED, "paged on-call engineer (" + severity + ")"), d);
        }

        @ParameterizedTest
        @EnumSource(value = Severity.class, names = {"LOW", "MEDIUM"})
        void filesBugBelowThreshold(Severity severity) {
            Decision d = engineering.handle(ticket(Category.OTHER, severity));
            assertEquals(Decision.handled(Outcome.ESCALATED, "filed engineering bug report"), d);
        }
    }
}
