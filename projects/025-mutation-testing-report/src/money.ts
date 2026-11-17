/**
 * Money as an immutable integer amount of minor units (cents).
 *
 * Floating-point currency arithmetic is the classic source of off-by-a-cent
 * bugs, so every value is stored as a safe integer and every operation that
 * can produce a fraction (percentages, ratios) goes through one explicit
 * rounding function.
 */

import { InvoiceError } from "./errors.js";

export type Currency = "USD" | "EUR" | "GBP";

export const SUPPORTED_CURRENCIES: readonly Currency[] = ["USD", "EUR", "GBP"];

export class Money {
  private constructor(
    readonly cents: number,
    readonly currency: Currency,
  ) {}

  static of(cents: number, currency: Currency = "USD"): Money {
    if (!Number.isSafeInteger(cents)) {
      throw new InvoiceError("INVALID_AMOUNT", `Amount must be a safe integer of cents, got ${cents}`);
    }
    if (!SUPPORTED_CURRENCIES.includes(currency)) {
      throw new InvoiceError("UNSUPPORTED_CURRENCY", `Unsupported currency: ${currency}`);
    }
    return new Money(cents, currency);
  }

  static zero(currency: Currency = "USD"): Money {
    return new Money(0, currency);
  }

  add(other: Money): Money {
    this.assertSameCurrency(other);
    return Money.of(this.cents + other.cents, this.currency);
  }

  subtract(other: Money): Money {
    this.assertSameCurrency(other);
    return Money.of(this.cents - other.cents, this.currency);
  }

  /** Multiply by an integer quantity; exact, so no rounding involved. */
  times(quantity: number): Money {
    if (!Number.isInteger(quantity)) {
      throw new InvoiceError("INVALID_QUANTITY", `Quantity must be an integer, got ${quantity}`);
    }
    return Money.of(this.cents * quantity, this.currency);
  }

  /**
   * Take a percentage of this amount, expressed in basis points
   * (1 bp = 0.01%, so 825 bp = 8.25%). Rounds half-to-even.
   */
  percentage(basisPoints: number): Money {
    return Money.of(roundHalfEven((this.cents * basisPoints) / 10_000), this.currency);
  }

  /** The smaller of two amounts — used to cap discounts. */
  min(other: Money): Money {
    this.assertSameCurrency(other);
    return this.cents <= other.cents ? this : other;
  }

  isNegative(): boolean {
    return this.cents < 0;
  }

  equals(other: Money): boolean {
    return this.cents === other.cents && this.currency === other.currency;
  }

  /**
   * Split this amount across weights so the parts always sum back to the
   * original (largest-remainder method). Used to spread an order-level
   * discount over line items for per-line tax.
   */
  allocate(weights: readonly number[]): Money[] {
    if (weights.length === 0) {
      throw new InvoiceError("INVALID_ALLOCATION", "Cannot allocate across zero weights");
    }
    if (weights.some((w) => w < 0)) {
      throw new InvoiceError("INVALID_ALLOCATION", "Allocation weights must be non-negative");
    }
    const total = weights.reduce((sum, w) => sum + w, 0);
    if (total === 0) {
      // Nothing to weight by: everything lands on the first share.
      return weights.map((_, i) => Money.of(i === 0 ? this.cents : 0, this.currency));
    }

    const exact = weights.map((w) => (this.cents * w) / total);
    const floors = exact.map(Math.floor);
    let remainder = this.cents - floors.reduce((sum, c) => sum + c, 0);

    // Hand leftover cents to the shares with the largest fractional parts.
    // Array.prototype.sort is stable (ES2019+), so equal fractions keep index
    // order and the earlier share wins — no explicit tiebreaker needed.
    const order = exact
      .map((value, index) => ({ index, fraction: value - Math.floor(value) }))
      .sort((a, b) => b.fraction - a.fraction);

    const bonus = new Set<number>();
    for (const { index } of order) {
      if (remainder === 0) break;
      bonus.add(index);
      remainder -= 1;
    }
    return floors.map((c, i) => Money.of(bonus.has(i) ? c + 1 : c, this.currency));
  }

  /** Human-readable, e.g. "USD 12.34" or "USD -0.05". */
  format(): string {
    const sign = this.cents < 0 ? "-" : "";
    const abs = Math.abs(this.cents);
    const major = Math.floor(abs / 100);
    const minor = String(abs % 100).padStart(2, "0");
    return `${this.currency} ${sign}${major}.${minor}`;
  }

  toString(): string {
    return this.format();
  }

  private assertSameCurrency(other: Money): void {
    if (other.currency !== this.currency) {
      throw new InvoiceError(
        "CURRENCY_MISMATCH",
        `Cannot combine ${this.currency} with ${other.currency}`,
      );
    }
  }
}

/**
 * Banker's rounding: halves go to the nearest even integer, which removes
 * the upward bias of always rounding .5 up across many line items.
 */
export function roundHalfEven(value: number): number {
  const floor = Math.floor(value);
  const diff = value - floor;
  // Tolerate float noise such as 2.4999999999 from (cents * bp) / 10000.
  const EPSILON = 1e-9;
  // Equivalent mutants: `>`/`>=` only differ when diff lands exactly on 0.5±1e-9,
  // which no realistic cents × basis-points input can produce.
  // Stryker disable next-line EqualityOperator: boundary is unobservable (see MUTATION_REPORT.md)
  if (diff > 0.5 + EPSILON) return floor + 1;
  // Stryker disable next-line EqualityOperator: boundary is unobservable (see MUTATION_REPORT.md)
  if (diff < 0.5 - EPSILON) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}
