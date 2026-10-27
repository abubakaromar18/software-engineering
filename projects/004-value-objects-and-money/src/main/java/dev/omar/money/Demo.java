package dev.omar.money;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Locale;

/** Small walkthrough of the API: run with {@code java -cp target/classes dev.omar.money.Demo}. */
public final class Demo {

    private Demo() {
    }

    public static void main(String[] args) {
        Currency usd = Currency.USD;

        // A dinner bill: line items, sales tax rounded HALF_UP, then a 20% tip.
        List<Money> items = List.of(
                Money.of("18.50", usd),
                Money.of("22.00", usd).times(2),
                Money.of("7.25", usd));
        Money subtotal = items.stream().collect(Money.summing(usd));
        Money tax = subtotal.times(new BigDecimal("0.0825"), RoundingMode.HALF_UP);
        Money tip = subtotal.times(new BigDecimal("0.20"), RoundingMode.HALF_UP);
        Money total = subtotal.plus(tax).plus(tip);

        System.out.println("Subtotal: " + subtotal);
        System.out.println("Tax:      " + tax);
        System.out.println("Tip:      " + tip);
        System.out.println("Total:    " + total + "  (" + total.format(Locale.US) + ")");

        List<Money> shares = total.split(3);
        System.out.println("Split 3 ways: " + shares + " -> sums to " + Money.sum(usd, shares));

        // Revenue share 70/20/10 of an amount that does not divide evenly.
        Money revenue = Money.of("100.01", usd);
        System.out.println("100.01 split 70/20/10: " + revenue.allocate(70, 20, 10));

        // Zero-decimal and three-decimal currencies.
        System.out.println("JPY 1000 split 3 ways: " + Money.of("1000", Currency.JPY).split(3));
        System.out.println("BHD: " + Money.of("1.234", Currency.of("BHD")));

        // Guard rails.
        try {
            Money.of("0.001", usd);
        } catch (ArithmeticException e) {
            System.out.println("Rejected: " + e.getMessage());
        }
        try {
            Money.of("1", usd).plus(Money.of("1", Currency.EUR));
        } catch (CurrencyMismatchException e) {
            System.out.println("Rejected: " + e.getMessage());
        }
    }
}
