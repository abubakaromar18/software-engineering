import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as before from "../src/dip/before.js";
import * as after from "../src/dip/after.js";
import { OrderError, type Email, type OrderLine } from "../src/dip/types.js";

const NOW = new Date("2026-10-25T17:30:00.000Z");
const lines: OrderLine[] = [
  { sku: "TEA", priceCents: 899, quantity: 2 },
  { sku: "MUG", priceCents: 1250, quantity: 1 },
];

describe("DIP parity: injected dependencies, identical behaviour", () => {
  // The "before" version can only be controlled through global state:
  // the real Date (faked here) and a reset hook into the module.
  beforeEach(() => {
    vi.useFakeTimers({ now: NOW });
    before.testHooks.reset();
  });
  afterEach(() => vi.useRealTimers());

  it("places the same orders and sends the same emails", () => {
    const mailer = new after.OutboxMailer();
    const orders = new after.InMemoryOrderRepository();
    const afterService = after.createOrderService({ mailer, orders, clock: { now: () => NOW } });
    const beforeService = new before.OrderService();

    for (const email of ["ada@example.com", "grace@example.org"]) {
      const b = beforeService.placeOrder(email, lines);
      const a = afterService.placeOrder(email, lines);
      expect(a).toEqual(b);
      expect(orders.find(a.id)).toEqual(before.testHooks.storedOrder(b.id));
    }
    expect(mailer.sent).toEqual(before.testHooks.sentEmails());
    expect(mailer.sent[0]).toEqual({
      to: "ada@example.com",
      subject: "Order ORD-00001 confirmed",
      body: "Thanks for your order ORD-00001. Total: $30.48.",
    });
  });

  it.each<[string, string, OrderLine[]]>([
    ["bad email", "not-an-email", lines],
    ["no lines", "a@b.co", []],
    ["zero quantity", "a@b.co", [{ sku: "X", priceCents: 1, quantity: 0 }]],
    ["negative price", "a@b.co", [{ sku: "X", priceCents: -1, quantity: 1 }]],
  ])("both reject %s and have no side effects", (_name, email, orderLines) => {
    const mailer = new after.OutboxMailer();
    const afterService = after.createOrderService({ mailer });
    const message = (run: () => unknown): string => {
      try {
        run();
        return "no error";
      } catch (error) {
        return (error as Error).message;
      }
    };
    const expected = message(() => new before.OrderService().placeOrder(email, orderLines));
    expect(message(() => afterService.placeOrder(email, orderLines))).toBe(expected);
    expect(expected).not.toBe("no error");
    expect(mailer.sent).toEqual(before.testHooks.sentEmails());
    expect(mailer.sent).toHaveLength(0);
  });
});

describe("DIP payoff: the policy is testable with plain fakes", () => {
  it("needs no global clock, no reset hooks, just constructor arguments", () => {
    const sent: Email[] = [];
    const service = new after.OrderService({
      mailer: { send: (email) => void sent.push(email) },
      orders: new after.InMemoryOrderRepository(),
      clock: { now: () => new Date("2030-01-01T00:00:00Z") },
      ids: { next: () => "FIXED-ID" },
    });
    const order = service.placeOrder("ada@example.com", lines);
    expect(order).toEqual({ id: "FIXED-ID", email: "ada@example.com", totalCents: 3048, placedAt: "2030-01-01T00:00:00.000Z" });
    expect(sent.map((e) => e.subject)).toEqual(["Order FIXED-ID confirmed"]);
  });

  it("a failing mailer surfaces to the caller after the order is saved", () => {
    const orders = new after.InMemoryOrderRepository();
    const service = after.createOrderService({
      orders,
      ids: new after.SequentialIds(42),
      mailer: { send: () => { throw new Error("SMTP down"); } },
    });
    expect(() => service.placeOrder("ada@example.com", lines)).toThrow("SMTP down");
    // Documents current behaviour: persistence happens first. An outbox pattern would make this atomic.
    expect(orders.find("ORD-00042")).toBeDefined();
  });

  it("independent instances do not share state", () => {
    const first = after.createOrderService().placeOrder("a@b.co", lines);
    const second = after.createOrderService().placeOrder("a@b.co", lines);
    expect(first.id).toBe(second.id);
  });

  it("validation errors are domain errors", () => {
    expect(() => after.createOrderService().placeOrder("bad", lines)).toThrow(OrderError);
  });
});
