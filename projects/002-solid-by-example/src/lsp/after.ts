/**
 * LSP — AFTER.
 *
 * The hierarchy now models what each account can actually do:
 *
 *   Account (balance, deposit)
 *     ├── TimeDepositAccount
 *     └── WithdrawableAccount (+ withdraw)
 *           ├── CheckingAccount
 *           └── OverdraftAccount
 *
 * Every WithdrawableAccount keeps the withdraw() contract, so collectFees can
 * accept any of them without special cases, and the compiler rejects a time
 * deposit before the code ever runs.
 */
import { assertCents, type Cents } from "../shared/money.js";
import { InsufficientFundsError, type FeeReport } from "./types.js";

export interface Account {
  readonly id: string;
  readonly balance: Cents;
  deposit(amount: Cents): void;
}

export interface WithdrawableAccount extends Account {
  /** Contract: succeeds for every amount <= balance; never makes balance lower than allowed. */
  withdraw(amount: Cents): void;
}

/** Shared deposit/balance behaviour. Not exported as a type callers can depend on. */
abstract class BaseAccount implements Account {
  protected balanceCents: Cents = 0;

  constructor(readonly id: string) {}

  get balance(): Cents {
    return this.balanceCents;
  }

  deposit(amount: Cents): void {
    assertCents(amount, "Deposit");
    this.balanceCents += amount;
  }
}

export class TimeDepositAccount extends BaseAccount {}

export class CheckingAccount extends BaseAccount implements WithdrawableAccount {
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

export class OverdraftAccount extends CheckingAccount {
  constructor(id: string, private readonly overdraftLimit: Cents) {
    super(id);
    assertCents(overdraftLimit, "Overdraft limit");
  }

  protected override availableToWithdraw(): Cents {
    return this.balanceCents + this.overdraftLimit;
  }
}

/** Same algorithm as before; the type now guarantees every element can honour withdraw(). */
export function collectFees(accounts: readonly WithdrawableAccount[], fee: Cents): FeeReport {
  let charged = 0;
  for (const account of accounts) {
    if (account.balance >= fee) {
      account.withdraw(fee);
      charged++;
    }
  }
  return { charged, skipped: accounts.length - charged };
}
