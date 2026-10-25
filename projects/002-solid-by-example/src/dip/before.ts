/**
 * DIP — BEFORE.
 *
 * The high-level policy (OrderService) constructs its low-level details
 * itself: a concrete mailer, a concrete database table, the system clock and a
 * hidden id counter. The arrows point the wrong way, from policy to detail, so:
 *   - swapping SMTP for a queue means editing OrderService;
 *   - tests must reach into module-level state and fake the global clock;
 *   - nothing documents what OrderService actually needs.
 *
 * The "SMTP" and "SQL" classes are simulated in memory so this runs anywhere.
 */
import { confirmationEmail, totalOf, type Email, type Order, type OrderLine } from "./types.js";

// Module-level state standing in for a real SMTP server and SQL database.
const smtpOutbox: Email[] = [];
const ordersTable = new Map<string, Order>();
let nextOrderNumber = 1;

class SmtpMailer {
  send(email: Email): void {
    smtpOutbox.push(email);
  }
}

class SqlOrderTable {
  insert(order: Order): void {
    ordersTable.set(order.id, order);
  }
}

export class OrderService {
  private readonly mailer = new SmtpMailer();
  private readonly table = new SqlOrderTable();

  placeOrder(email: string, lines: readonly OrderLine[]): Order {
    const totalCents = totalOf(email, lines);
    const order: Order = {
      id: `ORD-${String(nextOrderNumber++).padStart(5, "0")}`,
      email,
      totalCents,
      placedAt: new Date().toISOString(),
    };
    this.table.insert(order);
    this.mailer.send(confirmationEmail(order));
    return order;
  }
}

/**
 * The tell-tale sign of hidden dependencies: tests need a back door into the
 * module's globals. The "after" version needs nothing like this.
 */
export const testHooks = {
  sentEmails: (): readonly Email[] => [...smtpOutbox],
  storedOrder: (id: string): Order | undefined => ordersTable.get(id),
  reset(): void {
    smtpOutbox.length = 0;
    ordersTable.clear();
    nextOrderNumber = 1;
  },
};
