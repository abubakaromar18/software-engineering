/**
 * LSP — BEFORE.
 *
 * Account promises "withdraw(n) succeeds whenever n <= balance". The
 * TimeDepositAccount subclass breaks that promise: it inherits withdraw() and
 * then refuses to honour it. Any code written against Account (collectFees
 * below) now has to know about the subclass, or it crashes at runtime.
 *
 * OverdraftAccount is a *legal* subclass: it weakens the precondition (allows
 * more withdrawals), which the substitution principle permits.
 */
import { assertCents, type Cents } from "../shared/money.js";
import { AccountError, InsufficientFundsError, type FeeReport } from "./types.js";

export class Account {
  protected balanceCents: Cents = 0;

  constructor(readonly id: string) {}

  get balance(): Cents {
    return this.balanceCents;
  }

  deposit(amount: Cents): void {
    assertCents(amount, "Deposit");
    this.balanceCents += amount;
  }

  withdraw(amount: Cents): void {
    assertCents(amount, "Withdrawal");
    if (amount > this.availableToWithdraw()) {
      throw new InsufficientFundsError(`Account ${this.id} cannot withdraw ${amount}`);
    }
    this.balanceCents -= amount;
  }

  protected availableToWithdraw(): Cents {
    return this.balanceCents;
  }
}

export class OverdraftAccount extends Account {
  constructor(id: string, private readonly overdraftLimit: Cents) {
    super(id);
    assertCents(overdraftLimit, "Overdraft limit");
  }

  protected override availableToWithdraw(): Cents {
    return this.balanceCents + this.overdraftLimit;
  }
}

export class TimeDepositAccount extends Account {
  // The violation: a subclass that strengthens the precondition to "never".
  override withdraw(_amount: Cents): never {
    throw new AccountError(`Time deposit ${this.id} cannot be withdrawn before maturity`);
  }
}

/** Charges `fee` to every account that can afford it. Written against the base type. */
export function collectFees(accounts: readonly Account[], fee: Cents): FeeReport {
  let charged = 0;
  for (const account of accounts) {
    if (account.balance >= fee) {
      account.withdraw(fee); // throws for TimeDepositAccount despite enough balance
      charged++;
    }
  }
  return { charged, skipped: accounts.length - charged };
}
