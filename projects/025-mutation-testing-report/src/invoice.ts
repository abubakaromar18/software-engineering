/**
 * Invoice calculation pipeline:
 *
 *   gross  →  volume discount  →  subtotal  →  coupon (allocated per line)  →  tax  →  total
 *
 * Each stage is a pure function over immutable Money values, which is what
 * makes the module cheap to test exhaustively and to mutation-test quickly.
 */

import { InvoiceError } from "./errors.js";
import { Money, type Currency } from "./money.js";
import {
  assertCouponApplicable,
  couponDiscount,
  validateTiers,
  volumeDiscount,
  type Coupon,
  type VolumeTier,
} from "./discounts.js";
import { DEFAULT_TAX_TABLE, taxFor, validateTaxTable, type TaxCategory, type TaxTable } from "./tax.js";

export interface LineInput {
  readonly sku: string;
  readonly unitPriceCents: number;
  readonly quantity: number;
  readonly category?: TaxCategory;
}

export interface InvoiceOptions {
  readonly currency?: Currency;
  readonly tiers?: readonly VolumeTier[];
  readonly coupon?: Coupon;
  /** ISO date the invoice is issued on; drives coupon validity. */
  readonly issuedOn: string;
  readonly taxTable?: TaxTable;
  /**
   * What to do with a coupon that does not apply. "reject" records the reason
   * on the invoice and carries on (checkout UX); "throw" fails fast (APIs).
   */
  readonly invalidCoupon?: "reject" | "throw";
}

export interface InvoiceLine {
  readonly sku: string;
  readonly quantity: number;
  readonly category: TaxCategory;
  readonly gross: Money;
  readonly volumeDiscount: Money;
  readonly couponDiscount: Money;
  readonly taxable: Money;
  readonly tax: Money;
  readonly total: Money;
}

export interface Invoice {
  readonly currency: Currency;
  readonly lines: readonly InvoiceLine[];
  readonly gross: Money;
  readonly volumeDiscount: Money;
  readonly subtotal: Money;
  readonly couponDiscount: Money;
  readonly tax: Money;
  readonly total: Money;
  readonly appliedCoupon?: string;
  readonly couponRejection?: string;
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function validateLine(line: LineInput, index: number): void {
  if (line.sku.trim() === "") {
    throw new InvoiceError("INVALID_LINE", `Line ${index}: sku must not be blank`);
  }
  if (!Number.isSafeInteger(line.unitPriceCents) || line.unitPriceCents < 0) {
    throw new InvoiceError("INVALID_LINE", `Line ${index}: unitPriceCents must be a non-negative integer`);
  }
  if (!Number.isInteger(line.quantity) || line.quantity < 1) {
    throw new InvoiceError("INVALID_LINE", `Line ${index}: quantity must be a positive integer`);
  }
}

export function calculateInvoice(lines: readonly LineInput[], options: InvoiceOptions): Invoice {
  const currency = options.currency ?? "USD";
  const tiers = options.tiers ?? [];
  const taxTable = options.taxTable ?? DEFAULT_TAX_TABLE;

  if (lines.length === 0) {
    throw new InvoiceError("INVALID_LINE", "An invoice needs at least one line");
  }
  if (!ISO_DATE.test(options.issuedOn)) {
    throw new InvoiceError("INVALID_LINE", `issuedOn must be an ISO date (YYYY-MM-DD), got ${options.issuedOn}`);
  }
  lines.forEach(validateLine);
  validateTiers(tiers);
  validateTaxTable(taxTable);

  // Stage 1: per-line gross and volume discount.
  const priced = lines.map((line) => {
    const gross = Money.of(line.unitPriceCents, currency).times(line.quantity);
    const volume = volumeDiscount(gross, line.quantity, tiers);
    return { line, gross, volume, net: gross.subtract(volume) };
  });
  const subtotal = sum(priced.map((p) => p.net), currency);

  // Stage 2: coupon at order level, then spread across lines by net value.
  const coupon = resolveCoupon(options, subtotal);
  const shares = coupon.discount.allocate(priced.map((p) => p.net.cents));

  // Stage 3: per-line tax on what the customer actually pays for that line.
  const invoiceLines: InvoiceLine[] = priced.map((p, i) => {
    const share = shares[i] ?? Money.zero(currency);
    const category = p.line.category ?? "standard";
    const taxable = p.net.subtract(share);
    const tax = taxFor(taxable, category, taxTable);
    return {
      sku: p.line.sku,
      quantity: p.line.quantity,
      category,
      gross: p.gross,
      volumeDiscount: p.volume,
      couponDiscount: share,
      taxable,
      tax,
      total: taxable.add(tax),
    };
  });

  const tax = sum(invoiceLines.map((l) => l.tax), currency);
  return {
    currency,
    lines: invoiceLines,
    gross: sum(priced.map((p) => p.gross), currency),
    volumeDiscount: sum(priced.map((p) => p.volume), currency),
    subtotal,
    couponDiscount: coupon.discount,
    tax,
    total: subtotal.subtract(coupon.discount).add(tax),
    ...(coupon.applied !== undefined && { appliedCoupon: coupon.applied }),
    ...(coupon.rejection !== undefined && { couponRejection: coupon.rejection }),
  };
}

interface CouponOutcome {
  readonly discount: Money;
  readonly applied?: string;
  readonly rejection?: string;
}

function resolveCoupon(options: InvoiceOptions, subtotal: Money): CouponOutcome {
  const { coupon } = options;
  if (coupon === undefined) return { discount: Money.zero(subtotal.currency) };
  try {
    assertCouponApplicable(coupon, subtotal, options.issuedOn);
  } catch (error) {
    if (options.invalidCoupon === "throw" || !(error instanceof InvoiceError)) throw error;
    return { discount: Money.zero(subtotal.currency), rejection: error.message };
  }
  return { discount: couponDiscount(coupon, subtotal), applied: coupon.code };
}

function sum(amounts: readonly Money[], currency: Currency): Money {
  return amounts.reduce((acc, m) => acc.add(m), Money.zero(currency));
}
