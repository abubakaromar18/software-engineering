/**
 * BASELINE SUITE — frozen on purpose.
 *
 * This is the kind of suite that passes code review: it exercises every
 * module, hits ~83% line coverage, and every test is green. Mutation testing
 * shows how little of the behaviour it actually pins down. Do not "fix"
 * this file; see test/strengthened/ and MUTATION_REPORT.md instead.
 */

import { describe, expect, it } from "vitest";
import {
  Money,
  calculateInvoice,
  couponDiscount,
  roundHalfEven,
  selectTier,
  taxFor,
  DEFAULT_TAX_TABLE,
  type Coupon,
} from "../../src/index.js";

const tiers = [
  { minQuantity: 10, basisPoints: 500 },
  { minQuantity: 50, basisPoints: 1000 },
];

describe("Money", () => {
  it("adds and subtracts", () => {
    const a = Money.of(1000);
    const b = Money.of(250);
    expect(a.add(b).cents).toBe(1250);
    expect(a.subtract(b).cents).toBeGreaterThan(0);
  });

  it("multiplies", () => {
    expect(Money.of(199).times(3).cents).toBe(597);
  });

  it("takes a percentage", () => {
    expect(Money.of(10000).percentage(825).cents).toBe(825);
  });

  it("formats", () => {
    expect(Money.of(1234).format()).toContain("12");
  });

  it("allocates", () => {
    const parts = Money.of(100).allocate([1, 1, 1]);
    expect(parts).toHaveLength(3);
  });

  it("rejects bad input", () => {
    expect(() => Money.of(1.5)).toThrow();
    expect(() => Money.of(100).add(Money.of(1, "EUR"))).toThrow();
  });

  it("rounds", () => {
    expect(roundHalfEven(2.5)).toBe(2);
    expect(roundHalfEven(2.7)).toBe(3);
  });
});

describe("discounts", () => {
  it("selects a tier", () => {
    expect(selectTier(tiers, 60)).toBeDefined();
    expect(selectTier(tiers, 1)).toBeUndefined();
  });

  it("applies a percent coupon", () => {
    const coupon: Coupon = { code: "SAVE10", kind: { type: "percent", basisPoints: 1000 } };
    expect(couponDiscount(coupon, Money.of(5000)).cents).toBe(500);
  });

  it("applies a fixed coupon", () => {
    const coupon: Coupon = { code: "FIVE", kind: { type: "fixed", amountCents: 500 } };
    expect(couponDiscount(coupon, Money.of(5000)).cents).toBeGreaterThan(0);
  });
});

describe("tax", () => {
  it("computes standard tax", () => {
    expect(taxFor(Money.of(10000), "standard", DEFAULT_TAX_TABLE).cents).toBe(825);
  });
});

describe("calculateInvoice", () => {
  it("calculates a simple invoice", () => {
    const invoice = calculateInvoice(
      [
        { sku: "PEN", unitPriceCents: 150, quantity: 20 },
        { sku: "APPLE", unitPriceCents: 80, quantity: 5, category: "food" },
      ],
      {
        issuedOn: "2026-11-17",
        tiers,
        coupon: {
          code: "WELCOME",
          kind: { type: "percent", basisPoints: 1000 },
          minSpendCents: 1000,
          validFrom: "2026-01-01",
          validUntil: "2026-12-31",
        },
      },
    );
    expect(invoice.lines).toHaveLength(2);
    expect(invoice.total.cents).toBeGreaterThan(0);
    expect(invoice.appliedCoupon).toBe("WELCOME");
  });

  it("records an expired coupon", () => {
    const invoice = calculateInvoice([{ sku: "PEN", unitPriceCents: 150, quantity: 1 }], {
      issuedOn: "2027-02-01",
      coupon: { code: "OLD", kind: { type: "fixed", amountCents: 100 }, validUntil: "2026-12-31" },
    });
    expect(invoice.couponRejection).toBeDefined();
  });

  it("rejects an empty invoice", () => {
    expect(() => calculateInvoice([], { issuedOn: "2026-11-17" })).toThrow();
  });
});
