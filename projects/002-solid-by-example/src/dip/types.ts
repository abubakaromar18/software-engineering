import { assertCents, formatCents, type Cents } from "../shared/money.js";

export interface OrderLine {
  readonly sku: string;
  readonly priceCents: Cents;
  readonly quantity: number;
}

export interface Order {
  readonly id: string;
  readonly email: string;
  readonly totalCents: Cents;
  readonly placedAt: string; // ISO-8601
}

export interface Email {
  readonly to: string;
  readonly subject: string;
  readonly body: string;
}

export class OrderError extends Error {
  override readonly name: string = "OrderError";
}

/**
 * Business rules shared by both versions. DIP is about where the details live,
 * not about changing the rules, so the policy is identical before and after.
 */
export function totalOf(email: string, lines: readonly OrderLine[]): Cents {
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) throw new OrderError(`Invalid email: ${email}`);
  if (lines.length === 0) throw new OrderError("An order needs at least one line");
  return lines.reduce((sum, line) => {
    if (!Number.isInteger(line.quantity) || line.quantity <= 0) {
      throw new OrderError(`Quantity for ${line.sku} must be a positive integer`);
    }
    assertCents(line.priceCents, `Price for ${line.sku}`);
    return sum + line.priceCents * line.quantity;
  }, 0);
}

export function confirmationEmail(order: Order): Email {
  return {
    to: order.email,
    subject: `Order ${order.id} confirmed`,
    body: `Thanks for your order ${order.id}. Total: ${formatCents(order.totalCents)}.`,
  };
}
