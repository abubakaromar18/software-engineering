/** Machine-readable error codes so callers can branch without parsing messages. */
export type InvoiceErrorCode =
  | "INVALID_AMOUNT"
  | "INVALID_QUANTITY"
  | "UNSUPPORTED_CURRENCY"
  | "CURRENCY_MISMATCH"
  | "INVALID_ALLOCATION"
  | "INVALID_LINE"
  | "INVALID_TIERS"
  | "COUPON_EXPIRED"
  | "COUPON_NOT_YET_VALID"
  | "COUPON_MIN_SPEND"
  | "INVALID_COUPON";

export class InvoiceError extends Error {
  constructor(
    readonly code: InvoiceErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "InvoiceError";
  }
}
