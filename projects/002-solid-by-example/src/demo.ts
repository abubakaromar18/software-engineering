/**
 * Runs each principle's "before" and "after" code side by side on the same
 * input and prints whether the observable behaviour matches.
 *
 *   npm run demo
 */
import * as srpBefore from "./srp/before.js";
import * as srpAfter from "./srp/after.js";
import * as ocpBefore from "./ocp/before.js";
import * as ocpAfter from "./ocp/after.js";
import * as lspBefore from "./lsp/before.js";
import * as lspAfter from "./lsp/after.js";
import * as ispBefore from "./isp/before.js";
import * as ispAfter from "./isp/after.js";
import * as dipBefore from "./dip/before.js";
import * as dipAfter from "./dip/after.js";
import { formatCents } from "./shared/money.js";

function section(title: string, before: unknown, after: unknown, note: string): void {
  const same = JSON.stringify(before) === JSON.stringify(after);
  console.log(`\n=== ${title} ===`);
  console.log(typeof after === "string" ? after : JSON.stringify(after, null, 2));
  console.log(`before === after: ${same ? "yes" : "NO"}`);
  console.log(`payoff: ${note}`);
}

// SRP
const customer = { id: "C-042", name: "Ada Lovelace", taxExempt: false };
const items = [
  { sku: "BK-101", description: "Analytical Engine guide", unitPriceCents: 2999, quantity: 2 },
  { sku: "PN-007", description: "Fountain pen", unitPriceCents: 1450, quantity: 1 },
];
section(
  "S — Single Responsibility (invoices)",
  new srpBefore.InvoiceService().createInvoice("INV-1", customer, items, 0.0825),
  new srpAfter.InvoiceService().createInvoice("INV-1", customer, items, 0.0825),
  "tax rules, layout and storage can now change and be tested independently.",
);

// OCP
const parcel = { weightKg: 2.3, distanceKm: 640 };
const methods = ["standard", "express", "overnight"];
const calculator = new ocpAfter.ShippingCalculator();
section(
  "O — Open/Closed (shipping quotes)",
  methods.map((m) => formatCents(ocpBefore.shippingCost(m, parcel))),
  methods.map((m) => formatCents(calculator.cost(m, parcel))),
  "a new carrier service is a register() call, not an edit to a switch.",
);

// LSP
function lspRun<A extends { deposit(n: number): void; readonly balance: number }>(
  accounts: A[],
  collect: (a: A[]) => unknown,
): unknown {
  accounts.forEach((a) => a.deposit(5_000));
  return { report: collect(accounts), balances: accounts.map((a) => a.balance) };
}
section(
  "L — Liskov Substitution (fee collection over withdrawable accounts)",
  lspRun([new lspBefore.Account("A"), new lspBefore.OverdraftAccount("B", 1_000)], (a) => lspBefore.collectFees(a, 250)),
  lspRun([new lspAfter.CheckingAccount("A"), new lspAfter.OverdraftAccount("B", 1_000)], (a) => lspAfter.collectFees(a, 250)),
  "a TimeDepositAccount can no longer be passed to collectFees: the compiler rejects it.",
);

// ISP
const memo = { title: "Q3 memo", pages: ["p1", "p2"] };
section(
  "I — Interface Segregation (office devices)",
  ispBefore.printAll(new ispBefore.BasicPrinter("HP-1"), [memo]),
  ispAfter.printAll(new ispAfter.BasicPrinter("HP-1"), [memo]),
  "BasicPrinter implements only print(); no stub methods that throw.",
);

// DIP
const fixedClock = { now: () => new Date("2026-10-25T12:00:00Z") };
const lines = [{ sku: "TEA-1", priceCents: 899, quantity: 3 }];
const dipAfterOrder = dipAfter.createOrderService({ clock: fixedClock }).placeOrder("ada@example.com", lines);
// The "before" service reads the real system clock and cannot be told otherwise,
// so its timestamp is masked for the comparison.
const dipBeforeOrder = new dipBefore.OrderService().placeOrder("ada@example.com", lines);
section(
  "D — Dependency Inversion (order placement, timestamp masked)",
  { ...dipBeforeOrder, placedAt: "<now>" },
  { ...dipAfterOrder, placedAt: "<now>" },
  "the service receives its mailer, repository, clock and ids, so tests inject fakes.",
);
