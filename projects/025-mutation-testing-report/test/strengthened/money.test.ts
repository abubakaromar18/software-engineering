import { describe, expect, it } from "vitest";
import { InvoiceError, Money, roundHalfEven } from "../../src/index.js";

/** Assert both that it throws InvoiceError and with which code — a bare toThrow() kills almost nothing. */
function expectCode(fn: () => unknown, code: string): void {
  try {
    fn();
  } catch (error) {
    expect(error).toBeInstanceOf(InvoiceError);
    expect((error as InvoiceError).code).toBe(code);
    expect((error as InvoiceError).name).toBe("InvoiceError");
    return;
  }
  expect.fail(`expected InvoiceError ${code}`);
}

describe("Money construction", () => {
  it("defaults to USD and keeps the given currency otherwise", () => {
    expect(Money.of(5).currency).toBe("USD");
    expect(Money.of(5, "GBP").currency).toBe("GBP");
    expect(Money.zero().equals(Money.of(0, "USD"))).toBe(true);
    expect(Money.zero("EUR").currency).toBe("EUR");
  });

  it.each([1.5, Number.NaN, Number.POSITIVE_INFINITY, 2 ** 53])("rejects non-safe-integer amount %s", (cents) => {
    expectCode(() => Money.of(cents), "INVALID_AMOUNT");
  });

  it("accepts negative and boundary safe integers", () => {
    expect(Money.of(-1).cents).toBe(-1);
    expect(Money.of(Number.MAX_SAFE_INTEGER).cents).toBe(Number.MAX_SAFE_INTEGER);
  });

  it("rejects unknown currencies (runtime input bypassing the type)", () => {
    expectCode(() => Money.of(1, "JPY" as never), "UNSUPPORTED_CURRENCY");
  });

  it("error messages identify the offending value", () => {
    expect(() => Money.of(1.5)).toThrow("got 1.5");
    expect(() => Money.of(1, "JPY" as never)).toThrow("JPY");
  });
});

describe("Money arithmetic", () => {
  it("adds and subtracts exactly", () => {
    expect(Money.of(1000).add(Money.of(250)).cents).toBe(1250);
    expect(Money.of(1000).subtract(Money.of(250)).cents).toBe(750);
    expect(Money.of(250).subtract(Money.of(1000)).cents).toBe(-750);
  });

  it("refuses to mix currencies in add, subtract and min", () => {
    const usd = Money.of(1);
    const eur = Money.of(1, "EUR");
    expectCode(() => usd.add(eur), "CURRENCY_MISMATCH");
    expectCode(() => usd.subtract(eur), "CURRENCY_MISMATCH");
    expectCode(() => usd.min(eur), "CURRENCY_MISMATCH");
    expect(() => usd.add(eur)).toThrow("Cannot combine USD with EUR");
  });

  it("multiplies by integer quantities only", () => {
    expect(Money.of(199).times(3).cents).toBe(597);
    expect(Money.of(199).times(0).cents).toBe(0);
    expectCode(() => Money.of(199).times(1.5), "INVALID_QUANTITY");
    expect(() => Money.of(1).times(0.5)).toThrow("got 0.5");
  });

  it("takes basis-point percentages with banker's rounding", () => {
    expect(Money.of(10000).percentage(825).cents).toBe(825);
    expect(Money.of(1234).percentage(1000).cents).toBe(123); // 123.4
    expect(Money.of(1235).percentage(1000).cents).toBe(124); // 123.5 → even 124
    expect(Money.of(1225).percentage(1000).cents).toBe(122); // 122.5 → even 122
    expect(Money.of(1236).percentage(1000).cents).toBe(124); // 123.6
    expect(Money.of(5, "EUR").percentage(10000).currency).toBe("EUR");
  });

  it("min returns the smaller value, preferring the receiver on ties", () => {
    const a = Money.of(5);
    const b = Money.of(7);
    expect(a.min(b)).toBe(a);
    expect(b.min(a)).toBe(a);
    const tie = Money.of(5);
    expect(a.min(tie)).toBe(a);
  });

  it("isNegative is strict about zero", () => {
    expect(Money.of(-1).isNegative()).toBe(true);
    expect(Money.of(0).isNegative()).toBe(false);
    expect(Money.of(1).isNegative()).toBe(false);
  });

  it("equals compares both amount and currency", () => {
    expect(Money.of(1).equals(Money.of(1))).toBe(true);
    expect(Money.of(1).equals(Money.of(2))).toBe(false);
    expect(Money.of(1).equals(Money.of(1, "EUR"))).toBe(false);
  });
});

describe("Money.allocate", () => {
  const cents = (parts: Money[]) => parts.map((p) => p.cents);

  it("splits evenly when it can", () => {
    expect(cents(Money.of(90).allocate([1, 1, 1]))).toEqual([30, 30, 30]);
  });

  it("gives leftover cents to the earliest shares on equal fractions", () => {
    expect(cents(Money.of(100).allocate([1, 1, 1]))).toEqual([34, 33, 33]);
    expect(cents(Money.of(101).allocate([1, 1, 1]))).toEqual([34, 34, 33]);
  });

  it("gives leftover cents to the largest fractional remainders", () => {
    // exact: 14.2857, 28.5714, 57.1428 → floors 14, 28, 57 (sum 99); 28.57 has the largest fraction
    expect(cents(Money.of(100).allocate([1, 2, 4]))).toEqual([14, 29, 57]);
    // exact: 3.333, 6.667 → largest fraction is the second share
    expect(cents(Money.of(10).allocate([1, 2]))).toEqual([3, 7]);
  });

  it("always sums back to the original amount", () => {
    for (const amount of [0, 1, 7, 99, 1001, 123457]) {
      const parts = Money.of(amount).allocate([3, 0, 5, 11, 2]);
      expect(parts.reduce((s, p) => s + p.cents, 0)).toBe(amount);
    }
  });

  it("gives zero-weight shares nothing", () => {
    expect(cents(Money.of(10).allocate([0, 1]))).toEqual([0, 10]);
  });

  it("puts everything on the first share when all weights are zero", () => {
    expect(cents(Money.of(10).allocate([0, 0, 0]))).toEqual([10, 0, 0]);
  });

  it("keeps the currency", () => {
    expect(Money.of(10, "GBP").allocate([1, 1]).every((p) => p.currency === "GBP")).toBe(true);
    expect(Money.of(10, "GBP").allocate([0, 0]).every((p) => p.currency === "GBP")).toBe(true);
  });

  it("rejects empty and negative weights", () => {
    expectCode(() => Money.of(10).allocate([]), "INVALID_ALLOCATION");
    expectCode(() => Money.of(10).allocate([1, -1]), "INVALID_ALLOCATION");
    expect(() => Money.of(10).allocate([])).toThrow("zero weights");
    expect(() => Money.of(10).allocate([-1])).toThrow("non-negative");
  });
});

describe("Money formatting", () => {
  it.each([
    [1234, "USD 12.34"],
    [5, "USD 0.05"],
    [100, "USD 1.00"],
    [0, "USD 0.00"],
    [-5, "USD -0.05"],
    [-1234, "USD -12.34"],
  ])("formats %i cents as %s", (amount, expected) => {
    expect(Money.of(amount).format()).toBe(expected);
    expect(String(Money.of(amount))).toBe(expected);
  });
});

describe("roundHalfEven", () => {
  it.each([
    [2.4, 2],
    [2.5, 2],
    [2.6, 3],
    [3.5, 4],
    [0.5, 0],
    [1.5, 2],
    [-0.5, 0],
    [-1.5, -2],
    [-2.5, -2],
    [7, 7],
  ])("rounds %d to %d", (value, expected) => {
    expect(roundHalfEven(value)).toBe(expected);
  });

  it("treats float noise around .5 as an exact half", () => {
    expect(roundHalfEven(2.5 - 1e-12)).toBe(2);
    expect(roundHalfEven(3.5 + 1e-12)).toBe(4);
    expect(roundHalfEven(2.5 + 1e-6)).toBe(3);
    expect(roundHalfEven(3.5 - 1e-6)).toBe(3);
  });
});
