// Presentation code: the magic-number rule is not applied to this layer.
import { readFileSync } from "node:fs";

export const formatPrice = (amount) => `$${amount.toFixed(2)}`;
export const template = () => readFileSync("price.html", "utf8");
