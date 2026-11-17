import { describe, expect, it } from "vitest";
import {
  DEFAULT_TAX_TABLE,
  InvoiceError,
  Money,
  calculateInvoice,
  taxFor,
  validateLine,
  validateTaxTable,
  type Coupon,
  type Invoice,
  type LineInput,
} from "../../src/index.js";

const tiers = [
  { minQuantity: 10, basisPoints: 500 },
  { minQuantity: 50, basisPoints: 1000 },
];

const welcome: Coupon = {
  code: "WELCOME",
  kind: { type: "percent", basisPoints: 1000 },
  minSpendCents: 1000,
  validFrom: "2026-01-01",
  validUntil: "2026-12-31",
};

const basket: LineInput[] = [
  { sku: "PEN", unitPriceCents: 150, quantity: 20 },
  { sku: "APPLE", unitPriceCents: 80, quantity: 5, category: "food" },
];

/** Flatten Money fields to cents so whole invoices compare with one toEqual. */
function summary(invoice: Invoice) {
  return {
    gross: invoice.gross.cents,
    volumeDiscount: invoice.volumeDiscount.cents,
    subtotal: invoice.subtotal.cents,
    couponDiscount: invoice.couponDiscount.cents,
    tax: invoice.tax.cents,
    total: invoice.total.cents,
    lines: invoice.lines.map((l) => ({
      sku: l.sku,
      quantity: l.quantity,
      category: l.category,
      gross: l.gross.cents,
      volumeDiscount: l.volumeDiscount.cents,
      couponDiscount: l.couponDiscount.cents,
      taxable: l.taxable.cents,
      tax: l.tax.cents,
      total: l.total.cents,
    })),
  };
}

function codeOf(fn: () => unknown): string | undefined {
  try {
    fn();
  } catch (error) {
    return error instanceof InvoiceError ? error.code : "NOT_AN_INVOICE_ERROR";
  }
  return undefined;
}

describe("calculateInvoice — worked example", () => {
  it("matches a hand-calculated invoice to the cent", () => {
    // PEN:   20 × 1.50 = 30.00, 5% tier → 28.50; coupon share 2.85 → 25.65; 8.25% tax 2.116 → 2.12
    // APPLE:  5 × 0.80 =  4.00, no tier →  4.00; coupon share 0.40 →  3.60; 2% food tax 0.072 → 0.07
    const invoice = calculateInvoice(basket, { issuedOn: "2026-11-17", tiers, coupon: welcome });
    expect(summary(invoice)).toEqual({
      gross: 3400,
      volumeDiscount: 150,
      subtotal: 3250,
      couponDiscount: 325,
      tax: 219,
      total: 3144,
      lines: [
        { sku: "PEN", quantity: 20, category: "standard", gross: 3000, volumeDiscount: 150, couponDiscount: 285, taxable: 2565, tax: 212, total: 2777 },
        { sku: "APPLE", quantity: 5, category: "food", gross: 400, volumeDiscount: 0, couponDiscount: 40, taxable: 360, tax: 7, total: 367 },
      ],
    });
    expect(invoice.appliedCoupon).toBe("WELCOME");
    expect("couponRejection" in invoice).toBe(false);
    expect(invoice.currency).toBe("USD");
  });

  it("line totals always reconcile with the invoice total", () => {
    const lines: LineInput[] = [
      { sku: "A", unitPriceCents: 333, quantity: 3 },
      { sku: "B", unitPriceCents: 101, quantity: 7, category: "reduced" },
      { sku: "C", unitPriceCents: 999, quantity: 1, category: "exempt" },
    ];
    const invoice = calculateInvoice(lines, {
      issuedOn: "2026-11-17",
      coupon: { code: "X", kind: { type: "fixed", amountCents: 100 } },
    });
    const shares = invoice.lines.map((l) => l.couponDiscount.cents);
    // weights 999:707:999 → exact 36.93, 26.14, 36.93 → floors 36+26+36 = 98; two spare cents go to the .93s
    expect(shares).toEqual([37, 26, 37]);
    expect(invoice.lines.reduce((s, l) => s + l.total.cents, 0)).toBe(invoice.total.cents);
    expect(invoice.lines.map((l) => l.tax.cents)).toEqual([79, 34, 0]);
  });
});

describe("calculateInvoice — options", () => {
  it("defaults: USD, no tiers, standard tax, no coupon", () => {
    const invoice = calculateInvoice([{ sku: "A", unitPriceCents: 10000, quantity: 100 }], { issuedOn: "2026-11-17" });
    expect(invoice.volumeDiscount.cents).toBe(0);
    expect(invoice.tax.cents).toBe(82_500);
    expect(invoice.total.cents).toBe(1_082_500);
    expect(invoice.couponDiscount.cents).toBe(0);
    expect("appliedCoupon" in invoice).toBe(false);
    expect("couponRejection" in invoice).toBe(false);
  });

  it("uses the requested currency throughout", () => {
    const invoice = calculateInvoice([{ sku: "A", unitPriceCents: 100, quantity: 1 }], { issuedOn: "2026-11-17", currency: "EUR" });
    expect(invoice.currency).toBe("EUR");
    expect(invoice.total.currency).toBe("EUR");
    expect(invoice.lines[0]?.tax.currency).toBe("EUR");
  });

  it("uses a custom tax table", () => {
    const table = { ...DEFAULT_TAX_TABLE, standard: 2000 };
    const invoice = calculateInvoice([{ sku: "A", unitPriceCents: 1000, quantity: 1 }], { issuedOn: "2026-11-17", taxTable: table });
    expect(invoice.tax.cents).toBe(200);
  });

  it("records a rejected coupon and charges full price by default", () => {
    const invoice = calculateInvoice([{ sku: "A", unitPriceCents: 500, quantity: 1 }], { issuedOn: "2026-11-17", coupon: welcome });
    expect(invoice.couponRejection).toBe("Coupon WELCOME requires a subtotal of at least USD 10.00");
    expect(invoice.couponDiscount.cents).toBe(0);
    expect(invoice.couponDiscount.currency).toBe("USD");
    expect("appliedCoupon" in invoice).toBe(false);
    expect(invoice.total.cents).toBe(541);
  });

  it("throws on a rejected coupon when asked to", () => {
    expect(
      codeOf(() =>
        calculateInvoice([{ sku: "A", unitPriceCents: 500, quantity: 1 }], { issuedOn: "2027-01-01", coupon: welcome, invalidCoupon: "throw" }),
      ),
    ).toBe("COUPON_EXPIRED");
  });

  it("never swallows programming errors from the coupon check", () => {
    const broken = { code: undefined, kind: { type: "fixed", amountCents: 1 } } as unknown as Coupon;
    expect(() => calculateInvoice([{ sku: "A", unitPriceCents: 500, quantity: 1 }], { issuedOn: "2026-11-17", coupon: broken })).toThrow(TypeError);
  });
});

describe("calculateInvoice — validation", () => {
  const ok = { issuedOn: "2026-11-17" };

  it("needs at least one line", () => {
    expect(codeOf(() => calculateInvoice([], ok))).toBe("INVALID_LINE");
    expect(() => calculateInvoice([], ok)).toThrow("at least one line");
  });

  it.each(["2026-1-17", "17/11/2026", "", "2026-11-17T00:00:00Z", "x2026-11-17"])("rejects issuedOn %j", (issuedOn) => {
    expect(codeOf(() => calculateInvoice(basket, { issuedOn }))).toBe("INVALID_LINE");
    expect(() => calculateInvoice(basket, { issuedOn })).toThrow(`ISO date (YYYY-MM-DD), got ${issuedOn}`);
  });

  it("validates tiers and tax tables before pricing", () => {
    expect(codeOf(() => calculateInvoice(basket, { ...ok, tiers: [{ minQuantity: 0, basisPoints: 1 }] }))).toBe("INVALID_TIERS");
    expect(codeOf(() => calculateInvoice(basket, { ...ok, taxTable: { ...DEFAULT_TAX_TABLE, food: -1 } }))).toBe("INVALID_LINE");
  });

  it.each([
    ["blank sku", { sku: " ", unitPriceCents: 1, quantity: 1 }, "sku"],
    ["negative price", { sku: "A", unitPriceCents: -1, quantity: 1 }, "unitPriceCents"],
    ["fractional price", { sku: "A", unitPriceCents: 1.5, quantity: 1 }, "unitPriceCents"],
    ["zero quantity", { sku: "A", unitPriceCents: 1, quantity: 0 }, "quantity"],
    ["fractional quantity", { sku: "A", unitPriceCents: 1, quantity: 1.5 }, "quantity"],
  ])("rejects a line with %s", (_name, line, field) => {
    expect(codeOf(() => validateLine(line, 3))).toBe("INVALID_LINE");
    expect(() => validateLine(line, 3)).toThrow(`Line 3: ${field}`);
  });

  it("accepts free items", () => {
    expect(() => validateLine({ sku: "GIFT", unitPriceCents: 0, quantity: 1 }, 0)).not.toThrow();
  });
});

describe("tax", () => {
  it("applies each category's rate", () => {
    const base = Money.of(10_000);
    expect(taxFor(base, "standard", DEFAULT_TAX_TABLE).cents).toBe(825);
    expect(taxFor(base, "reduced", DEFAULT_TAX_TABLE).cents).toBe(500);
    expect(taxFor(base, "food", DEFAULT_TAX_TABLE).cents).toBe(200);
    expect(taxFor(base, "exempt", DEFAULT_TAX_TABLE).cents).toBe(0);
  });

  it("never taxes a negative base", () => {
    const tax = taxFor(Money.of(-100, "EUR"), "standard", DEFAULT_TAX_TABLE);
    expect(tax.cents).toBe(0);
    expect(tax.currency).toBe("EUR");
    expect(taxFor(Money.of(0), "standard", DEFAULT_TAX_TABLE).cents).toBe(0);
  });

  it("validates rates are integers within 0..10000", () => {
    expect(() => validateTaxTable({ ...DEFAULT_TAX_TABLE, standard: 0 })).not.toThrow();
    expect(() => validateTaxTable({ ...DEFAULT_TAX_TABLE, standard: 10_000 })).not.toThrow();
    for (const bad of [-1, 10_001, 8.25]) {
      expect(codeOf(() => validateTaxTable({ ...DEFAULT_TAX_TABLE, reduced: bad }))).toBe("INVALID_LINE");
    }
    expect(() => validateTaxTable({ ...DEFAULT_TAX_TABLE, reduced: -1 })).toThrow("reduced");
  });

  it("ships a frozen default table", () => {
    expect(Object.isFrozen(DEFAULT_TAX_TABLE)).toBe(true);
  });
});
