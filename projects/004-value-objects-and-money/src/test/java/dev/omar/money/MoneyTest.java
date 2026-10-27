package dev.omar.money;

import static dev.omar.money.Currency.EUR;
import static dev.omar.money.Currency.JPY;
import static dev.omar.money.Currency.USD;
import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Locale;
import java.util.stream.Stream;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

class MoneyTest {

    private static Money usd(String amount) {
        return Money.of(amount, USD);
    }

    @Nested
    class Creation {

        @Test
        void storesMinorUnits() {
            assertEquals(1234, usd("12.34").minorUnits());
            assertEquals(1230, usd("12.3").minorUnits());
            assertEquals(500, Money.of("500", JPY).minorUnits());
        }

        @Test
        void amountHasCurrencyScale() {
            assertEquals(new BigDecimal("12.30"), usd("12.3").amount());
            assertEquals(new BigDecimal("500"), Money.of("500", JPY).amount());
        }

        @Test
        void trailingZerosBeyondPrecisionAreAccepted() {
            assertEquals(usd("1.5"), usd("1.50000"));
        }

        @Test
        void excessPrecisionIsRejectedWithoutRoundingMode() {
            ArithmeticException e = assertThrows(ArithmeticException.class, () -> usd("0.001"));
            assertTrue(e.getMessage().contains("RoundingMode"));
            assertThrows(ArithmeticException.class, () -> Money.of("1.5", JPY));
        }

        @ParameterizedTest
        @CsvSource({"HALF_UP, 0.13", "HALF_EVEN, 0.12", "DOWN, 0.12", "CEILING, 0.13"})
        void explicitRoundingMode(RoundingMode mode, String expected) {
            assertEquals(usd(expected), Money.of(new BigDecimal("0.125"), USD, mode));
        }

        @Test
        void amountsBeyondLongRangeAreRejected() {
            assertThrows(ArithmeticException.class, () -> usd("100000000000000000000"));
        }

        @Test
        void nullsAreRejected() {
            assertThrows(NullPointerException.class, () -> Money.ofMinor(1, null));
            assertThrows(NullPointerException.class, () -> Money.of((BigDecimal) null, USD));
        }
    }

    @Nested
    class ValueSemantics {

        @Test
        void equalAmountsAreEqualRegardlessOfInputScale() {
            // BigDecimal("1.0").equals(BigDecimal("1.00")) is false; Money avoids that trap.
            assertEquals(usd("1.0"), usd("1.00"));
            assertEquals(usd("1.0").hashCode(), usd("1.00").hashCode());
        }

        @Test
        void sameAmountInDifferentCurrenciesIsNotEqual() {
            assertNotEquals(usd("1.00"), Money.of("1.00", EUR));
        }

        @Test
        void operationsReturnNewInstancesAndLeaveOperandsUntouched() {
            Money a = usd("10.00");
            Money b = a.plus(usd("5.00"));
            assertEquals(usd("10.00"), a);
            assertEquals(usd("15.00"), b);
        }

        @Test
        void worksAsMapKey() {
            var totals = new java.util.HashMap<Money, String>();
            totals.put(usd("9.90"), "found");
            assertEquals("found", totals.get(Money.ofMinor(990, USD)));
        }
    }

    @Nested
    class Arithmetic {

        @Test
        void addAndSubtract() {
            assertEquals(usd("0.30"), usd("0.10").plus(usd("0.20")));
            assertEquals(usd("-0.10"), usd("0.10").minus(usd("0.20")));
        }

        @Test
        void floatingPointClassicIsExact() {
            // 0.1 + 0.2 != 0.3 in double; here it is.
            assertEquals(usd("0.3"), usd("0.1").plus(usd("0.2")));
        }

        @Test
        void differentCurrenciesCannotBeCombined() {
            Money euros = Money.of("1", EUR);
            CurrencyMismatchException e =
                    assertThrows(CurrencyMismatchException.class, () -> usd("1").plus(euros));
            assertAll(
                    () -> assertEquals(USD, e.expected()),
                    () -> assertEquals(EUR, e.actual()));
            assertThrows(CurrencyMismatchException.class, () -> usd("1").minus(euros));
            assertThrows(CurrencyMismatchException.class, () -> usd("1").compareTo(euros));
        }

        @Test
        void sameCodeWithDifferentPrecisionIsAMismatch() {
            Money odd = Money.ofMinor(1, new Currency("USD", 3));
            assertThrows(CurrencyMismatchException.class, () -> usd("1").plus(odd));
        }

        @Test
        void negateAndAbs() {
            assertEquals(usd("-2.50"), usd("2.50").negated());
            assertEquals(usd("2.50"), usd("-2.50").abs());
            Money positive = usd("2.50");
            assertSame(positive, positive.abs());
        }

        @Test
        void multiplyByWholeNumber() {
            assertEquals(usd("59.97"), usd("19.99").times(3));
        }

        @ParameterizedTest
        @CsvSource({
            "100.00, 0.0825, HALF_UP,   8.25",
            "19.99,  0.0825, HALF_UP,   1.65",
            "0.05,   0.5,    HALF_EVEN, 0.02",
            "0.05,   0.5,    HALF_UP,   0.03"
        })
        void multiplyByDecimalRoundsAsRequested(String amount, String factor, RoundingMode mode, String expected) {
            assertEquals(usd(expected), usd(amount).times(new BigDecimal(factor), mode));
        }

        @Test
        void overflowThrowsInsteadOfWrapping() {
            Money max = Money.ofMinor(Long.MAX_VALUE, USD);
            assertThrows(ArithmeticException.class, () -> max.plus(Money.ofMinor(1, USD)));
            assertThrows(ArithmeticException.class, () -> max.times(2));
            assertThrows(ArithmeticException.class, () -> Money.ofMinor(Long.MIN_VALUE, USD).negated());
        }
    }

    @Nested
    class Comparison {

        @Test
        void ordersWithinCurrency() {
            assertTrue(usd("2").isGreaterThan(usd("1.99")));
            assertTrue(usd("-1").isLessThan(usd("0")));
            assertEquals(0, usd("1.0").compareTo(usd("1.00")));
        }

        @Test
        void signPredicates() {
            assertTrue(usd("0").isZero());
            assertTrue(usd("0.01").isPositive());
            assertTrue(usd("-0.01").isNegative());
            assertFalse(usd("0").isPositive());
        }
    }

    @Nested
    class Allocation {

        @Test
        void fowlerExampleFiveCentsThirtySeventy() {
            assertEquals(List.of(usd("0.02"), usd("0.03")), usd("0.05").allocate(3, 7));
        }

        @Test
        void oddCentGoesToLargestRemainder() {
            // Exact shares are 70.007, 20.002, 10.001: the leftover cent goes to the first part.
            assertEquals(List.of(usd("70.01"), usd("20.00"), usd("10.00")), usd("100.01").allocate(70, 20, 10));
        }

        @Test
        void splitIntoEqualParts() {
            assertEquals(List.of(usd("33.34"), usd("33.33"), usd("33.33")), usd("100").split(3));
            assertEquals(List.of(Money.of("334", JPY), Money.of("333", JPY), Money.of("333", JPY)),
                    Money.of("1000", JPY).split(3));
        }

        @Test
        void negativeAmountsSplitSymmetrically() {
            assertEquals(List.of(usd("-33.34"), usd("-33.33"), usd("-33.33")), usd("-100").split(3));
        }

        @Test
        void zeroRatioGetsNothing() {
            assertEquals(List.of(usd("0.01"), usd("0.00")), usd("0.01").allocate(1, 0));
        }

        @Test
        void hugeRatiosDoNotOverflow() {
            List<Money> parts = Money.ofMinor(Long.MAX_VALUE, USD).allocate(Long.MAX_VALUE, Long.MAX_VALUE);
            assertEquals(Money.ofMinor(Long.MAX_VALUE, USD), Money.sum(USD, parts));
        }

        @Test
        void invalidRatiosAreRejected() {
            Money m = usd("1");
            assertThrows(IllegalArgumentException.class, () -> m.allocate());
            assertThrows(IllegalArgumentException.class, () -> m.allocate(0, 0));
            assertThrows(IllegalArgumentException.class, () -> m.allocate(1, -1));
            assertThrows(IllegalArgumentException.class, () -> m.split(0));
        }
    }

    @Nested
    class Aggregation {

        @Test
        void sumOfEmptyIsZero() {
            assertEquals(Money.zero(USD), Money.sum(USD, List.of()));
        }

        @Test
        void collectorMatchesSum() {
            List<Money> amounts = List.of(usd("1.10"), usd("2.20"), usd("3.30"));
            assertEquals(usd("6.60"), amounts.stream().collect(Money.summing(USD)));
            assertEquals(usd("6.60"), amounts.parallelStream().collect(Money.summing(USD)));
        }

        @Test
        void sumRejectsMixedCurrencies() {
            assertThrows(CurrencyMismatchException.class,
                    () -> Stream.of(usd("1"), Money.of("1", EUR)).collect(Money.summing(USD)));
        }
    }

    @Nested
    class Text {

        @ParameterizedTest
        @ValueSource(strings = {"USD 12.34", "USD -0.05", "JPY 1000", "BHD 1.234"})
        void toStringRoundTripsThroughParse(String text) {
            assertEquals(text, Money.parse(text).toString());
        }

        @Test
        void toStringAlwaysShowsCurrencyScale() {
            assertEquals("USD 5.00", usd("5").toString());
        }

        @ParameterizedTest
        @ValueSource(strings = {"12.34", "USD", "USD twelve", "USD 1 2", "ZZZ 1.00"})
        void parseRejectsMalformedText(String text) {
            assertThrows(IllegalArgumentException.class, () -> Money.parse(text));
        }

        @Test
        void localeFormatting() {
            assertEquals("$1,234.50", usd("1234.5").format(Locale.US));
            assertEquals("PTS 10", Money.ofMinor(10, new Currency("PTS", 0)).format(Locale.US));
        }
    }
}
