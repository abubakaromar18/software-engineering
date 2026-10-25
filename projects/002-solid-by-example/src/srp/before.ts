/**
 * SRP — BEFORE.
 *
 * One class validates input, does the arithmetic, renders the text and keeps
 * the storage. Those are four reasons to change owned by four different people
 * (finance changes tax rules, design changes the layout, ops changes storage).
 * Any edit to one risks the other three, and none of them can be tested alone.
 */
import { assertCents, formatCents } from "../shared/money.js";
import { InvoiceError, type Customer, type LineItem, type StoredInvoice } from "./types.js";

export class InvoiceService {
  private readonly invoices = new Map<string, StoredInvoice>();

  createInvoice(id: string, customer: Customer, items: readonly LineItem[], taxRate: number): string {
    if (this.invoices.has(id)) throw new InvoiceError(`Invoice ${id} already exists`);
    if (items.length === 0) throw new InvoiceError("An invoice needs at least one line item");
    if (!(taxRate >= 0 && taxRate <= 1)) throw new InvoiceError(`Tax rate must be between 0 and 1, got ${taxRate}`);

    let subtotal = 0;
    let lines = "";
    for (const item of items) {
      if (!Number.isInteger(item.quantity) || item.quantity <= 0) {
        throw new InvoiceError(`Quantity for ${item.sku} must be a positive integer`);
      }
      assertCents(item.unitPriceCents, `Unit price for ${item.sku}`);
      const lineTotal = item.unitPriceCents * item.quantity;
      subtotal += lineTotal;
      lines += `${item.sku.padEnd(10)}${item.description.padEnd(24)}${String(item.quantity).padStart(4)} x ${formatCents(item.unitPriceCents).padStart(10)} = ${formatCents(lineTotal).padStart(11)}\n`;
    }
    const tax = customer.taxExempt ? 0 : Math.round(subtotal * taxRate);
    const total = subtotal + tax;

    this.invoices.set(id, { id, customerId: customer.id, subtotalCents: subtotal, taxCents: tax, totalCents: total });

    return (
      `INVOICE ${id}\n` +
      `Bill to: ${customer.name} (${customer.id})\n` +
      `${"-".repeat(64)}\n` +
      lines +
      `${"-".repeat(64)}\n` +
      `${"Subtotal".padEnd(52)}${formatCents(subtotal).padStart(12)}\n` +
      `${(customer.taxExempt ? "Tax (exempt)" : `Tax (${(taxRate * 100).toFixed(2)}%)`).padEnd(52)}${formatCents(tax).padStart(12)}\n` +
      `${"TOTAL".padEnd(52)}${formatCents(total).padStart(12)}\n`
    );
  }

  findInvoice(id: string): StoredInvoice | undefined {
    return this.invoices.get(id);
  }
}
