// Deliberately breaks the rules, so the demo has something to report.
import { merge } from "lodash";
import { formatPrice } from "../ui/format.js";

export function quote(base, quantity, customerTier, couponCode) {
  const discount = customerTier === "gold" ? 0.2 : 0;
  const total = base * quantity * (1 - discount);
  if (total > 1000) {
    return formatPrice(total * 0.95);
  }
  return formatPrice(total);
}

export const defaults = (overrides) => merge({ currency: "USD" }, overrides);
