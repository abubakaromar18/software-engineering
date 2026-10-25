/**
 * SRP — AFTER.
 *
 * Each class has a single reason to change:
 *   InvoiceCalculator   — pricing and tax rules (finance)
 *   InvoiceTextFormatter — presentation (design)
 *   InvoiceRepository   — persistence (ops)
 *   InvoiceService      — orchestration only: it owns the workflow, not the details
 *
 * The public API of InvoiceService is identical to the "before" version, so
 * callers do not change. The parity tests in test/srp.test.ts prove it.
 */
import { assertCents, formatCents, type Cents } from "../shared/money.js";
import { InvoiceError, type Customer, type LineItem, type StoredInvoice } from "./types.js";

export interface PricedLine {
  readonly item: LineItem;
  readonly lineTotalCents: Cents;
}

/** A fully priced invoice: the hand-off between calculation and presentation. */
export interface PricedInvoice {
  readonly id: string;
  readonly customer: Customer;
  readonly taxRate: number;
  readonly lines: readonly PricedLine[];
  readonly subtotalCents: Cents;
  readonly taxCents: Cents;
  readonly totalCents: Cents;
}

export class InvoiceCalculator {
  calculate(id: string, customer: Customer, items: readonly LineItem[], taxRate: number): PricedInvoice {
    if (items.length === 0) throw new InvoiceError("An invoice needs at least one line item");
    if (!(taxRate >= 0 && taxRate <= 1)) throw new InvoiceError(`Tax rate must be between 0 and 1, got ${taxRate}`);

    const lines = items.map((item) => {
      if (!Number.isInteger(item.quantity) || item.quantity <= 0) {
        throw new InvoiceError(`Quantity for ${item.sku} must be a positive integer`);
      }
      assertCents(item.unitPriceCents, `Unit price for ${item.sku}`);
      return { item, lineTotalCents: item.unitPriceCents * item.quantity };
    });
    const subtotalCents = lines.reduce((sum, line) => sum + line.lineTotalCents, 0);
    const taxCents = customer.taxExempt ? 0 : Math.round(subtotalCents * taxRate);
    return { id, customer, taxRate, lines, subtotalCents, taxCents, totalCents: subtotalCents + taxCents };
  }
}

/** Anything that can render a priced invoice. A PDF or HTML formatter would implement this too. */
export interface InvoiceFormatter {
  format(invoice: PricedInvoice): string;
}

export class InvoiceTextFormatter implements InvoiceFormatter {
  private static readonly WIDTH = 64;
  private static readonly LABEL_WIDTH = 52;

  format(invoice: PricedInvoice): string {
    const rule = "-".repeat(InvoiceTextFormatter.WIDTH);
    const { customer } = invoice;
    const taxLabel = customer.taxExempt ? "Tax (exempt)" : `Tax (${(invoice.taxRate * 100).toFixed(2)}%)`;
    return [
      `INVOICE ${invoice.id}`,
      `Bill to: ${customer.name} (${customer.id})`,
      rule,
      ...invoice.lines.map((line) => this.formatLine(line)),
      rule,
      this.formatTotal("Subtotal", invoice.subtotalCents),
      this.formatTotal(taxLabel, invoice.taxCents),
      this.formatTotal("TOTAL", invoice.totalCents),
      "",
    ].join("\n");
  }

  private formatLine({ item, lineTotalCents }: PricedLine): string {
    return (
      item.sku.padEnd(10) +
      item.description.padEnd(24) +
      String(item.quantity).padStart(4) +
      ` x ${formatCents(item.unitPriceCents).padStart(10)}` +
      ` = ${formatCents(lineTotalCents).padStart(11)}`
    );
  }

  private formatTotal(label: string, cents: Cents): string {
    return label.padEnd(InvoiceTextFormatter.LABEL_WIDTH) + formatCents(cents).padStart(12);
  }
}

export interface InvoiceRepository {
  exists(id: string): boolean;
  save(invoice: StoredInvoice): void;
  find(id: string): StoredInvoice | undefined;
}

export class InMemoryInvoiceRepository implements InvoiceRepository {
  private readonly invoices = new Map<string, StoredInvoice>();

  exists(id: string): boolean {
    return this.invoices.has(id);
  }

  save(invoice: StoredInvoice): void {
    this.invoices.set(invoice.id, invoice);
  }

  find(id: string): StoredInvoice | undefined {
    return this.invoices.get(id);
  }
}

export class InvoiceService {
  constructor(
    private readonly calculator: InvoiceCalculator = new InvoiceCalculator(),
    private readonly formatter: InvoiceFormatter = new InvoiceTextFormatter(),
    private readonly repository: InvoiceRepository = new InMemoryInvoiceRepository(),
  ) {}

  createInvoice(id: string, customer: Customer, items: readonly LineItem[], taxRate: number): string {
    if (this.repository.exists(id)) throw new InvoiceError(`Invoice ${id} already exists`);
    const invoice = this.calculator.calculate(id, customer, items, taxRate);
    this.repository.save({
      id,
      customerId: customer.id,
      subtotalCents: invoice.subtotalCents,
      taxCents: invoice.taxCents,
      totalCents: invoice.totalCents,
    });
    return this.formatter.format(invoice);
  }

  findInvoice(id: string): StoredInvoice | undefined {
    return this.repository.find(id);
  }
}
