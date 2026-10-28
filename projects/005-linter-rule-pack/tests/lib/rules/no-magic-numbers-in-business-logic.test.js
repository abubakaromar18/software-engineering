"use strict";

const rule = require("../../../lib/rules/no-magic-numbers-in-business-logic");
const { createRuleTester } = require("../../rule-tester");

const magic = (raw) => ({ messageId: "magicNumber", data: { raw } });

createRuleTester().run("no-magic-numbers-in-business-logic", rule, {
  valid: [
    // Named constants are the whole point.
    "const FREE_SHIPPING_THRESHOLD = 50; if (total > FREE_SHIPPING_THRESHOLD) ship();",
    "const MAX_RETRIES = -3;",
    "const TAX_RATE_V2 = 0.0825;",
    "const BIG_LIMIT = 9007199254740993n;",
    // Containers of a named constant are part of the constant.
    "const DISCOUNTS = { gold: 0.2, silver: 0.1 };",
    "const TIERS = [10, 20, [30, 40]];",
    "const LEVELS = Object.freeze({ low: 10, high: { max: 90 } });",
    "class Pricing { static VAT = 0.2; }",
    // Default allow-list.
    "const total = items.length + 1 - 0;",
    "if (index === -1) notFound();",
    // Array indexes are positions, not quantities.
    "const first = rows[2];",
    // Radix arguments.
    "const id = parseInt(raw, 10); const hex = Number.parseInt(raw, 16);",
    // Object keys are identifiers.
    "const messages = { 404: 'Not found' };",
    // Non-numeric literals are out of scope.
    "const label = 'Order #42';",
    // Options.
    { code: "const fee = amount * 0.03;", options: [{ allow: [0.03] }] },
    { code: "function page(size = 25) { return size; }", options: [{ ignoreDefaultParams: true }] },
    { code: "const maxItems = 10;", options: [{ constantPattern: "^max[A-Z]" }] },
  ],

  invalid: [
    {
      code: "if (total > 50) applyFreeShipping();",
      errors: [{ ...magic("50"), line: 1, column: 13, endColumn: 15 }],
    },
    {
      code: "const price = base * 1.2;",
      errors: [magic("1.2")],
    },
    {
      code: "if (balance < -100) freeze();",
      errors: [{ ...magic("-100"), column: 15, endColumn: 19 }],
    },
    {
      // A lowercase const is a variable that happens to be const, not a named constant.
      code: "const discount = 0.15;",
      errors: [magic("0.15")],
    },
    {
      // `let` can be reassigned, so it does not document a fixed business value.
      code: "let THRESHOLD = 500;",
      errors: [magic("500")],
    },
    {
      // Numbers inside an expression are still magic, even in a constant's initializer.
      code: "const LIMIT = compute(7);",
      errors: [magic("7")],
    },
    {
      code: "const order = { quantity: 12 };",
      errors: [magic("12")],
    },
    {
      code: "class Cart { limit = 30; }",
      errors: [magic("30")],
    },
    {
      code: "const big = 10n * amount;",
      errors: [magic("10n")],
    },
    {
      code: "function page(size = 25) { return size; }",
      errors: [magic("25")],
    },
    {
      code: "const first = rows[2];",
      options: [{ ignoreArrayIndexes: false }],
      errors: [magic("2")],
    },
    {
      // A custom allow-list replaces the default one.
      code: "const next = index + 1;",
      options: [{ allow: [0] }],
      errors: [magic("1")],
    },
    {
      code: "const n = parseFloat(raw, 10) * 3;",
      errors: [magic("10"), magic("3")],
    },
  ],
});
