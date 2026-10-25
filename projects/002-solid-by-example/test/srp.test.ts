import { describe, expect, it } from "vitest";
import * as before from "../src/srp/before.js";
import * as after from "../src/srp/after.js";
import { InvoiceError, type Customer, type LineItem } from "../src/srp/types.js";

const ada: Customer = { id: "C-1", name: "Ada", taxExempt: false };
const charity: Customer = { id: "C-2", name: "Kind Org", taxExempt: true };
const items: LineItem[] = [
  { sku: "BK-1", description: "Book", unitPriceCents: 1999, quantity: 3 },
  { sku: "PN-2", description: "Pen", unitPriceCents: 150, quantity: 1 },
];

type Service = { createInvoice: before.InvoiceService["createInvoice"]; findInvoice: before.InvoiceService["findInvoice"] };
const versions: [string, () => Service][] = [
  ["before", () => new before.InvoiceService()],
  ["after", () => new after.InvoiceService()],
];

describe("SRP parity: both versions behave identically", () => {
  const cases: [string, Customer, LineItem[], number][] = [
    ["taxable", ada, items, 0.0825],
    ["tax-exempt", charity, items, 0.0825],
    ["zero rate", ada, items, 0],
    ["rounding half up", ada, [{ sku: "X", description: "x", unitPriceCents: 10, quantity: 1 }], 0.05],
    ["large amounts", ada, [{ sku: "SRV", description: "Server", unitPriceCents: 1_234_567, quantity: 12 }], 0.2],
  ];

  it.each(cases)("renders the same text and stores the same record (%s)", (_name, customer, lineItems, rate) => {
    const [b, a] = versions.map(([, make]) => make()) as [Service, Service];
    expect(a.createInvoice("INV-9", customer, lineItems, rate)).toBe(b.createInvoice("INV-9", customer, lineItems, rate));
    expect(a.findInvoice("INV-9")).toEqual(b.findInvoice("INV-9"));
  });

  const invalid: [string, () => [Customer, LineItem[], number], string][] = [
    ["no items", () => [ada, [], 0.1], "at least one line item"],
    ["negative rate", () => [ada, items, -0.1], "between 0 and 1"],
    ["NaN rate", () => [ada, items, Number.NaN], "between 0 and 1"],
    ["zero qty", () => [ada, [{ ...items[0]!, quantity: 0 }], 0.1], "positive integer"],
    ["fractional qty", () => [ada, [{ ...items[0]!, quantity: 1.5 }], 0.1], "positive integer"],
    ["fractional price", () => [ada, [{ ...items[0]!, unitPriceCents: 9.5 }], 0.1], "integer number of cents"],
  ];

  describe.each(versions)("%s", (_version, make) => {
    it.each(invalid)("rejects %s", (_name, args, message) => {
      const service = make();
      expect(() => service.createInvoice("INV-1", ...args())).toThrow(message);
      expect(service.findInvoice("INV-1")).toBeUndefined();
    });

    it("rejects duplicate ids", () => {
      const service = make();
      service.createInvoice("INV-1", ada, items, 0.1);
      expect(() => service.createInvoice("INV-1", ada, items, 0.1)).toThrow(InvoiceError);
    });
  });

  it("matches a reviewed snapshot of the rendered invoice", () => {
    expect(new after.InvoiceService().createInvoice("INV-1", ada, items, 0.0825)).toMatchInlineSnapshot(`
      "INVOICE INV-1
      Bill to: Ada (C-1)
      ----------------------------------------------------------------
      BK-1      Book                       3 x     $19.99 =      $59.97
      PN-2      Pen                        1 x      $1.50 =       $1.50
      ----------------------------------------------------------------
      Subtotal                                                  $61.47
      Tax (8.25%)                                                $5.07
      TOTAL                                                     $66.54
      "
    `);
  });
});

describe("SRP payoff: each responsibility is usable on its own", () => {
  it("the calculator needs no formatter or storage", () => {
    const priced = new after.InvoiceCalculator().calculate("INV-1", ada, items, 0.1);
    expect(priced).toMatchObject({ subtotalCents: 6147, taxCents: 615, totalCents: 6762 });
  });

  it("a new output format plugs in without touching the calculator or service", () => {
    const csv: after.InvoiceFormatter = {
      format: (inv) => inv.lines.map((l) => `${l.item.sku},${l.lineTotalCents}`).concat(`TOTAL,${inv.totalCents}`).join("\n"),
    };
    const service = new after.InvoiceService(new after.InvoiceCalculator(), csv);
    expect(service.createInvoice("INV-1", ada, items, 0)).toBe("BK-1,5997\nPN-2,150\nTOTAL,6147");
  });

  it("storage can be replaced, e.g. with a spy", () => {
    const saved: string[] = [];
    const repo: after.InvoiceRepository = {
      exists: () => false,
      save: (inv) => void saved.push(inv.id),
      find: () => undefined,
    };
    new after.InvoiceService(undefined, undefined, repo).createInvoice("INV-7", ada, items, 0.1);
    expect(saved).toEqual(["INV-7"]);
  });
});
