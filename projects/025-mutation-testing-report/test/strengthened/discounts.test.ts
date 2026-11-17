import { describe, expect, it } from "vitest";
import {
  InvoiceError,
  Money,
  assertCouponApplicable,
  couponDiscount,
  selectTier,
  validateTiers,
  volumeDiscount,
  type Coupon,
} from "../../src/index.js";

const tiers = [
  { minQuantity: 10, basisPoints: 500 },
  { minQuantity: 50, basisPoints: 1000 },
];

function codeOf(fn: () => unknown): string | undefined {
  try {
    fn();
  } catch (error) {
    return error instanceof InvoiceError ? error.code : "NOT_AN_INVOICE_ERROR";
  }
  return undefined;
}

describe("volume tiers", () => {
  it("selects exactly at each threshold (inclusive)", () => {
    expect(selectTier(tiers, 9)).toBeUndefined();
    expect(selectTier(tiers, 10)).toEqual(tiers[0]);
    expect(selectTier(tiers, 49)).toEqual(tiers[0]);
    expect(selectTier(tiers, 50)).toEqual(tiers[1]);
    expect(selectTier(tiers, 500)).toEqual(tiers[1]);
    expect(selectTier([], 500)).toBeUndefined();
  });

  it("discounts the line by the selected tier", () => {
    expect(volumeDiscount(Money.of(10000), 10, tiers).cents).toBe(500);
    expect(volumeDiscount(Money.of(10000), 50, tiers).cents).toBe(1000);
    const none = volumeDiscount(Money.of(10000, "EUR"), 9, tiers);
    expect(none.cents).toBe(0);
    expect(none.currency).toBe("EUR");
  });

  it("accepts valid tiers including the 0 and 10000 bp extremes", () => {
    expect(() => validateTiers([])).not.toThrow();
    expect(() => validateTiers([{ minQuantity: 1, basisPoints: 0 }, { minQuantity: 2, basisPoints: 10_000 }])).not.toThrow();
  });

  it.each([
    ["zero minQuantity", [{ minQuantity: 0, basisPoints: 100 }], "minQuantity"],
    ["fractional minQuantity", [{ minQuantity: 1.5, basisPoints: 100 }], "minQuantity"],
    ["negative rate", [{ minQuantity: 1, basisPoints: -1 }], "basisPoints"],
    ["rate over 100%", [{ minQuantity: 1, basisPoints: 10_001 }], "basisPoints"],
    ["duplicate threshold", [{ minQuantity: 5, basisPoints: 1 }, { minQuantity: 5, basisPoints: 2 }], "sorted"],
    ["descending thresholds", [{ minQuantity: 5, basisPoints: 1 }, { minQuantity: 4, basisPoints: 2 }], "sorted"],
  ])("rejects %s", (_name, bad, message) => {
    expect(codeOf(() => validateTiers(bad))).toBe("INVALID_TIERS");
    expect(() => validateTiers(bad)).toThrow(message);
  });

  it("names the offending tier index", () => {
    expect(() => validateTiers([{ minQuantity: 1, basisPoints: 1 }, { minQuantity: 2, basisPoints: -1 }])).toThrow("Tier 1");
  });
});

describe("coupon applicability", () => {
  const base: Coupon = {
    code: "FALL",
    kind: { type: "fixed", amountCents: 100 },
    minSpendCents: 2000,
    validFrom: "2026-09-01",
    validUntil: "2026-11-30",
  };
  const enough = Money.of(2000);

  it("is valid on both inclusive edges of its window", () => {
    expect(codeOf(() => assertCouponApplicable(base, enough, "2026-09-01"))).toBeUndefined();
    expect(codeOf(() => assertCouponApplicable(base, enough, "2026-11-30"))).toBeUndefined();
  });

  it("is not valid the day before or the day after", () => {
    expect(codeOf(() => assertCouponApplicable(base, enough, "2026-08-31"))).toBe("COUPON_NOT_YET_VALID");
    expect(codeOf(() => assertCouponApplicable(base, enough, "2026-12-01"))).toBe("COUPON_EXPIRED");
  });

  it("requires the minimum spend, inclusive", () => {
    expect(codeOf(() => assertCouponApplicable(base, Money.of(1999), "2026-10-01"))).toBe("COUPON_MIN_SPEND");
    expect(() => assertCouponApplicable(base, Money.of(1999), "2026-10-01")).toThrow("at least USD 20.00");
  });

  it("treats missing constraints as unconstrained", () => {
    const open: Coupon = { code: "ANY", kind: { type: "fixed", amountCents: 1 } };
    expect(codeOf(() => assertCouponApplicable(open, Money.of(0), "1999-01-01"))).toBeUndefined();
  });

  it("rejects blank codes", () => {
    expect(codeOf(() => assertCouponApplicable({ ...base, code: "   " }, enough, "2026-10-01"))).toBe("INVALID_COUPON");
    expect(() => assertCouponApplicable({ ...base, code: "" }, enough, "2026-10-01")).toThrow("must not be blank");
  });

  it("explains the reason in the message", () => {
    expect(() => assertCouponApplicable(base, enough, "2026-08-31")).toThrow("FALL is valid from 2026-09-01");
    expect(() => assertCouponApplicable(base, enough, "2026-12-01")).toThrow("FALL expired on 2026-11-30");
  });
});

describe("coupon value", () => {
  const subtotal = Money.of(5000);

  it("percent coupons take a share of the subtotal", () => {
    expect(couponDiscount({ code: "P", kind: { type: "percent", basisPoints: 1000 } }, subtotal).cents).toBe(500);
  });

  it("percent coupons respect their cap", () => {
    const capped: Coupon = { code: "P", kind: { type: "percent", basisPoints: 5000, maxDiscountCents: 1500 } };
    expect(couponDiscount(capped, subtotal).cents).toBe(1500);
    const loose: Coupon = { code: "P", kind: { type: "percent", basisPoints: 1000, maxDiscountCents: 1500 } };
    expect(couponDiscount(loose, subtotal).cents).toBe(500);
  });

  it("fixed coupons take their face value", () => {
    expect(couponDiscount({ code: "F", kind: { type: "fixed", amountCents: 700 } }, subtotal).cents).toBe(700);
  });

  it("never discounts more than the subtotal", () => {
    expect(couponDiscount({ code: "F", kind: { type: "fixed", amountCents: 9999 } }, subtotal).cents).toBe(5000);
  });

  it("accepts 0 and 10000 bp but nothing outside", () => {
    expect(couponDiscount({ code: "P", kind: { type: "percent", basisPoints: 0 } }, subtotal).cents).toBe(0);
    expect(couponDiscount({ code: "P", kind: { type: "percent", basisPoints: 10_000 } }, subtotal).cents).toBe(5000);
    expect(codeOf(() => couponDiscount({ code: "P", kind: { type: "percent", basisPoints: -1 } }, subtotal))).toBe("INVALID_COUPON");
    expect(codeOf(() => couponDiscount({ code: "P", kind: { type: "percent", basisPoints: 10_001 } }, subtotal))).toBe("INVALID_COUPON");
    expect(() => couponDiscount({ code: "P", kind: { type: "percent", basisPoints: -1 } }, subtotal)).toThrow("0..10000 basis points");
  });

  it("rejects negative fixed amounts but allows zero", () => {
    expect(couponDiscount({ code: "F", kind: { type: "fixed", amountCents: 0 } }, subtotal).cents).toBe(0);
    expect(codeOf(() => couponDiscount({ code: "F", kind: { type: "fixed", amountCents: -1 } }, subtotal))).toBe("INVALID_COUPON");
    expect(() => couponDiscount({ code: "F", kind: { type: "fixed", amountCents: -1 } }, subtotal)).toThrow("must not be negative");
  });

  it("returns the subtotal's currency", () => {
    expect(couponDiscount({ code: "F", kind: { type: "fixed", amountCents: 1 } }, Money.of(10, "EUR")).currency).toBe("EUR");
  });
});
