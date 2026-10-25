import { describe, expect, it } from "vitest";
import * as before from "../src/lsp/before.js";
import * as after from "../src/lsp/after.js";
import { AccountError, InsufficientFundsError } from "../src/lsp/types.js";

interface Withdrawable {
  readonly balance: number;
  deposit(amount: number): void;
  withdraw(amount: number): void;
}

/**
 * The behavioural contract every withdrawable account must honour. Running it
 * against each implementation is how LSP is checked in practice: a subtype is
 * substitutable exactly when it passes its supertype's contract tests.
 */
function withdrawContract(name: string, make: () => Withdrawable): void {
  describe(`withdraw() contract: ${name}`, () => {
    it("allows withdrawing any amount up to the balance", () => {
      const account = make();
      account.deposit(1_000);
      account.withdraw(400);
      account.withdraw(600);
      expect(account.balance).toBe(0);
    });

    it("rejects invalid amounts without changing the balance", () => {
      const account = make();
      account.deposit(1_000);
      expect(() => account.withdraw(-1)).toThrow(RangeError);
      expect(() => account.withdraw(1.5)).toThrow(RangeError);
      expect(account.balance).toBe(1_000);
    });
  });
}

withdrawContract("before/Account", () => new before.Account("A"));
withdrawContract("before/OverdraftAccount", () => new before.OverdraftAccount("O", 500));
withdrawContract("after/CheckingAccount", () => new after.CheckingAccount("A"));
withdrawContract("after/OverdraftAccount", () => new after.OverdraftAccount("O", 500));

describe("LSP: the 'before' hierarchy contains a violating subtype", () => {
  it("TimeDepositAccount is an Account but cannot honour withdraw()", () => {
    const deposit = new before.TimeDepositAccount("T");
    deposit.deposit(10_000);
    expect(deposit).toBeInstanceOf(before.Account);
    expect(() => deposit.withdraw(100)).toThrow(AccountError);
  });

  it("so a client written against Account crashes mid-way, leaving partial side effects", () => {
    const checking = new before.Account("A");
    const deposit = new before.TimeDepositAccount("T");
    checking.deposit(1_000);
    deposit.deposit(1_000);
    expect(() => before.collectFees([checking, deposit], 100)).toThrow(AccountError);
    expect(checking.balance).toBe(900); // already charged before the crash
  });
});

describe("LSP parity: valid programs behave identically", () => {
  type Pair = [string, () => { accounts: Withdrawable[]; collect: (fee: number) => unknown }];
  const versions: Pair[] = [
    ["before", () => {
      const accounts = [new before.Account("A"), new before.OverdraftAccount("O", 300), new before.Account("Z")];
      return { accounts, collect: (fee) => before.collectFees(accounts, fee) };
    }],
    ["after", () => {
      const accounts = [new after.CheckingAccount("A"), new after.OverdraftAccount("O", 300), new after.CheckingAccount("Z")];
      return { accounts, collect: (fee) => after.collectFees(accounts, fee) };
    }],
  ];

  function scenario(make: Pair[1]): unknown {
    const { accounts, collect } = make();
    const [a, o] = accounts as [Withdrawable, Withdrawable];
    a.deposit(500);
    o.deposit(100);
    const log: unknown[] = [collect(150)];
    o.withdraw(350); // into the overdraft
    try {
      o.withdraw(51); // 1 cent beyond the overdraft limit
    } catch (error) {
      log.push(error instanceof InsufficientFundsError ? error.message : "unexpected");
    }
    log.push(collect(50), accounts.map((x) => x.balance));
    return log;
  }

  it("produces the same fee reports, errors and balances", () => {
    const [b, a] = versions.map(([, make]) => scenario(make));
    expect(a).toEqual(b);
    expect(a).toEqual([
      { charged: 1, skipped: 2 },
      "Account O cannot withdraw 51",
      { charged: 1, skipped: 2 },
      [300, -250, 0],
    ]);
  });

  it("time deposits keep the same deposit/balance behaviour", () => {
    const b = new before.TimeDepositAccount("T");
    const a = new after.TimeDepositAccount("T");
    for (const account of [a, b]) {
      account.deposit(2_500);
      account.deposit(0);
      expect(() => account.deposit(-5)).toThrow(RangeError);
    }
    expect(a.balance).toBe(b.balance);
  });
});

describe("LSP payoff: the type system now enforces substitutability", () => {
  it("a time deposit cannot be passed where withdrawals are required", () => {
    const deposit = new after.TimeDepositAccount("T");
    // @ts-expect-error TimeDepositAccount has no withdraw(); this line must not compile.
    const misuse = (): unknown => after.collectFees([deposit], 100);
    expect(typeof misuse).toBe("function"); // never invoked: the compiler already caught it
    expect("withdraw" in deposit).toBe(false);
  });
});
