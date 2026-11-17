/**
 * Discount rules: quantity-based volume tiers (per line) and order-level
 * coupons. These are deliberately rich in boundaries (>= vs >, inclusive
 * date windows, caps) because that is exactly where mutation testing finds
 * holes that line coverage hides.
 */

import { InvoiceError } from "./errors.js";
import { Money } from "./money.js";

/** Buy at least `minQuantity` units and get `basisPoints` off the line. */
export interface VolumeTier {
  readonly minQuantity: number;
  readonly basisPoints: number;
}

export function validateTiers(tiers: readonly VolumeTier[]): void {
  for (const [i, tier] of tiers.entries()) {
    if (!Number.isInteger(tier.minQuantity) || tier.minQuantity < 1) {
      throw new InvoiceError("INVALID_TIERS", `Tier ${i}: minQuantity must be a positive integer`);
    }
    if (tier.basisPoints < 0 || tier.basisPoints > 10_000) {
      throw new InvoiceError("INVALID_TIERS", `Tier ${i}: basisPoints must be within 0..10000`);
    }
    const previous = tiers[i - 1];
    if (previous && tier.minQuantity <= previous.minQuantity) {
      throw new InvoiceError("INVALID_TIERS", "Tiers must be sorted by strictly increasing minQuantity");
    }
  }
}

/** The best (highest-threshold) tier the quantity qualifies for, if any. */
export function selectTier(tiers: readonly VolumeTier[], quantity: number): VolumeTier | undefined {
  let selected: VolumeTier | undefined;
  for (const tier of tiers) {
    if (quantity >= tier.minQuantity) selected = tier;
  }
  return selected;
}

export function volumeDiscount(gross: Money, quantity: number, tiers: readonly VolumeTier[]): Money {
  const tier = selectTier(tiers, quantity);
  return tier ? gross.percentage(tier.basisPoints) : Money.zero(gross.currency);
}

export type CouponKind =
  | { readonly type: "percent"; readonly basisPoints: number; readonly maxDiscountCents?: number }
  | { readonly type: "fixed"; readonly amountCents: number };

export interface Coupon {
  readonly code: string;
  readonly kind: CouponKind;
  /** Order subtotal (after volume discounts) must be at least this much. */
  readonly minSpendCents?: number;
  /** Inclusive validity window as ISO dates (YYYY-MM-DD). */
  readonly validFrom?: string;
  readonly validUntil?: string;
}

/**
 * Throws an InvoiceError explaining why a coupon cannot be applied, or
 * returns normally if it can. Separating "is it applicable?" from "how much
 * is it worth?" keeps both functions small and individually testable.
 */
export function assertCouponApplicable(coupon: Coupon, subtotal: Money, onDate: string): void {
  if (coupon.code.trim() === "") {
    throw new InvoiceError("INVALID_COUPON", "Coupon code must not be blank");
  }
  // ISO-8601 calendar dates compare correctly as strings.
  if (coupon.validFrom !== undefined && onDate < coupon.validFrom) {
    throw new InvoiceError("COUPON_NOT_YET_VALID", `Coupon ${coupon.code} is valid from ${coupon.validFrom}`);
  }
  if (coupon.validUntil !== undefined && onDate > coupon.validUntil) {
    throw new InvoiceError("COUPON_EXPIRED", `Coupon ${coupon.code} expired on ${coupon.validUntil}`);
  }
  if (coupon.minSpendCents !== undefined && subtotal.cents < coupon.minSpendCents) {
    throw new InvoiceError(
      "COUPON_MIN_SPEND",
      `Coupon ${coupon.code} requires a subtotal of at least ${Money.of(coupon.minSpendCents, subtotal.currency).format()}`,
    );
  }
}

/** The coupon's value against a subtotal; never more than the subtotal itself. */
export function couponDiscount(coupon: Coupon, subtotal: Money): Money {
  const { kind } = coupon;
  let discount: Money;
  if (kind.type === "percent") {
    if (kind.basisPoints < 0 || kind.basisPoints > 10_000) {
      throw new InvoiceError("INVALID_COUPON", "Percent coupon must be within 0..10000 basis points");
    }
    discount = subtotal.percentage(kind.basisPoints);
    if (kind.maxDiscountCents !== undefined) {
      discount = discount.min(Money.of(kind.maxDiscountCents, subtotal.currency));
    }
  } else {
    if (kind.amountCents < 0) {
      throw new InvoiceError("INVALID_COUPON", "Fixed coupon amount must not be negative");
    }
    discount = Money.of(kind.amountCents, subtotal.currency);
  }
  return discount.min(subtotal);
}
