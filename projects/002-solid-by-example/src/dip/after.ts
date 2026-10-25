/**
 * DIP — AFTER.
 *
 * OrderService owns the abstractions it needs (Mailer, OrderRepository, Clock,
 * IdGenerator) and receives implementations through its constructor. Details
 * now depend on the policy's interfaces, not the other way round:
 *
 *   OrderService ──> «Mailer» <── OutboxMailer / SmtpMailer / QueueMailer...
 *                ──> «OrderRepository» <── InMemoryOrderRepository / SqlOrderRepository...
 *
 * createOrderService() is the composition root: the one place that knows which
 * concrete classes are used. Tests build the service with fakes instead.
 */
import { confirmationEmail, totalOf, type Email, type Order, type OrderLine } from "./types.js";

export interface Mailer {
  send(email: Email): void;
}

export interface OrderRepository {
  save(order: Order): void;
  find(id: string): Order | undefined;
}

export interface Clock {
  now(): Date;
}

export interface IdGenerator {
  next(): string;
}

export interface OrderServiceDeps {
  readonly mailer: Mailer;
  readonly orders: OrderRepository;
  readonly clock: Clock;
  readonly ids: IdGenerator;
}

export class OrderService {
  constructor(private readonly deps: OrderServiceDeps) {}

  placeOrder(email: string, lines: readonly OrderLine[]): Order {
    const totalCents = totalOf(email, lines);
    const order: Order = {
      id: this.deps.ids.next(),
      email,
      totalCents,
      placedAt: this.deps.clock.now().toISOString(),
    };
    this.deps.orders.save(order);
    this.deps.mailer.send(confirmationEmail(order));
    return order;
  }
}

// ---- Low-level details: each implements an interface the policy defined. ----

/** Collects messages in memory. A production build would swap in an SMTP adapter here. */
export class OutboxMailer implements Mailer {
  private readonly outbox: Email[] = [];

  send(email: Email): void {
    this.outbox.push(email);
  }

  get sent(): readonly Email[] {
    return [...this.outbox];
  }
}

export class InMemoryOrderRepository implements OrderRepository {
  private readonly orders = new Map<string, Order>();

  save(order: Order): void {
    this.orders.set(order.id, order);
  }

  find(id: string): Order | undefined {
    return this.orders.get(id);
  }
}

export const systemClock: Clock = { now: () => new Date() };

export class SequentialIds implements IdGenerator {
  constructor(private counter = 1, private readonly prefix = "ORD-") {}

  next(): string {
    return `${this.prefix}${String(this.counter++).padStart(5, "0")}`;
  }
}

/** Composition root: wires the default details. Override any of them by name. */
export function createOrderService(overrides: Partial<OrderServiceDeps> = {}): OrderService {
  return new OrderService({
    mailer: new OutboxMailer(),
    orders: new InMemoryOrderRepository(),
    clock: systemClock,
    ids: new SequentialIds(),
    ...overrides,
  });
}
