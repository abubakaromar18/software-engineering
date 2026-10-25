import type { Cents } from "../shared/money.js";

/** Shared by the "before" and "after" versions so their outputs are comparable. */
export interface LineItem {
  readonly sku: string;
  readonly description: string;
  readonly unitPriceCents: Cents;
  readonly quantity: number;
}

export interface Customer {
  readonly id: string;
  readonly name: string;
  readonly taxExempt: boolean;
}

/** The record that gets persisted for each invoice. */
export interface StoredInvoice {
  readonly id: string;
  readonly customerId: string;
  readonly subtotalCents: Cents;
  readonly taxCents: Cents;
  readonly totalCents: Cents;
}

export class InvoiceError extends Error {
  override readonly name: string = "InvoiceError";
}
