export class AccountError extends Error {
  override readonly name: string = "AccountError";
}

export class InsufficientFundsError extends AccountError {
  override readonly name: string = "InsufficientFundsError";
}

/** Result of charging a fee to every account in a list. */
export interface FeeReport {
  readonly charged: number;
  readonly skipped: number;
}
