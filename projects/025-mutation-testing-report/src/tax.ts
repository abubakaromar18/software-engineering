/**
 * Category-based sales tax. Tax is computed per line (after that line's
 * share of discounts) and rounded per line, which is how most real tax
 * engines behave and why `Money.allocate` must be exact.
 */

import { InvoiceError } from "./errors.js";
import { Money } from "./money.js";

export type TaxCategory = "standard" | "reduced" | "food" | "exempt";

/** Rates in basis points. */
export type TaxTable = Readonly<Record<TaxCategory, number>>;

export const DEFAULT_TAX_TABLE: TaxTable = Object.freeze({
  standard: 825,
  reduced: 500,
  food: 200,
  exempt: 0,
});

export function validateTaxTable(table: TaxTable): void {
  for (const [category, rate] of Object.entries(table)) {
    if (!Number.isInteger(rate) || rate < 0 || rate > 10_000) {
      throw new InvoiceError("INVALID_LINE", `Tax rate for ${category} must be an integer within 0..10000`);
    }
  }
}

export function taxFor(taxable: Money, category: TaxCategory, table: TaxTable): Money {
  // Taxing a negative base would hand the customer money back; clamp at zero.
  if (taxable.isNegative()) return Money.zero(taxable.currency);
  return taxable.percentage(table[category]);
}
