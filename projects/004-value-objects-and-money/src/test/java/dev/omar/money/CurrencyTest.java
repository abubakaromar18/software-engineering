package dev.omar.money;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

class CurrencyTest {

    @ParameterizedTest
    @CsvSource({"USD, 2", "EUR, 2", "JPY, 0", "BHD, 3", "KWD, 3"})
    void isoCurrenciesUseJdkMinorUnits(String code, int digits) {
        assertEquals(new Currency(code, digits), Currency.of(code));
    }

    @Test
    void equalityIsByValue() {
        assertEquals(Currency.USD, Currency.of("USD"));
        assertEquals(Currency.USD.hashCode(), new Currency("USD", 2).hashCode());
        assertNotEquals(Currency.USD, new Currency("USD", 3));
    }

    @Test
    void unknownCodeIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> Currency.of("ZZZ"));
    }

    @Test
    void currencyWithoutMinorUnitIsRejected() {
        // Gold (XAU) is in ISO 4217 but has no minor unit, so it cannot be counted in cents.
        assertThrows(IllegalArgumentException.class, () -> Currency.of("XAU"));
    }

    @ParameterizedTest
    @ValueSource(strings = {"usd", "US", "USDX", "U$D", ""})
    void malformedCodesAreRejected(String code) {
        assertThrows(IllegalArgumentException.class, () -> new Currency(code, 2));
    }

    @ParameterizedTest
    @ValueSource(ints = {-1, Currency.MAX_FRACTION_DIGITS + 1})
    void fractionDigitsAreBounded(int digits) {
        assertThrows(IllegalArgumentException.class, () -> new Currency("PTS", digits));
    }

    @Test
    void customUnitsCanBeModelled() {
        Currency points = new Currency("PTS", 0);
        assertEquals("PTS", points.toString());
    }
}
