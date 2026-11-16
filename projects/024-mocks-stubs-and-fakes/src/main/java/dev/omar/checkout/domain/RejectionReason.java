package dev.omar.checkout.domain;

/** Expected, recoverable reasons a checkout does not produce an order. */
public enum RejectionReason {
    EMPTY_CART,
    UNKNOWN_ITEM,
    OUT_OF_STOCK,
    PAYMENT_DECLINED,
    PAYMENT_UNAVAILABLE
}
