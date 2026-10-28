# rule-pack/no-magic-numbers-in-business-logic

Disallow unexplained numeric literals in business logic; require named constants instead.

✅ In `recommended` (as `error`).

## Why

`if (total > 50)` hides a business rule. Is 50 the free-shipping threshold? A fraud limit?
When the rule changes, which `50`s do you update? A named constant states the meaning once:

```js
const FREE_SHIPPING_THRESHOLD = 50;
if (total > FREE_SHIPPING_THRESHOLD) applyFreeShipping();
```

Core ESLint has `no-magic-numbers`, but it is noisy when turned on for a whole codebase
(layout code, animation timings, tests). This rule is meant to be **scoped to a layer**
with flat-config `files`, and it is stricter about what counts as a named constant.

## What is allowed

| Code | Why it passes |
|---|---|
| `const TAX_RATE = 0.0825;` | value of a `const` whose name matches `constantPattern` |
| `const RATES = Object.freeze({ gold: [0.2] });` | inside the object/array literal of a named constant |
| `class Pricing { static VAT = 0.2; }` | static class field with a constant-style name |
| `n + 1`, `i === -1`, `0` | in the `allow` list (default `[-1, 0, 1]`) |
| `rows[2]` | array index (`ignoreArrayIndexes`) |
| `parseInt(s, 10)` | radix argument |
| `{ 404: "Not found" }` | object key, not a quantity |

## What is reported

```js
if (total > 50) {}                 // 50
const discount = 0.15;             // lowercase name is a variable, not a constant
let THRESHOLD = 500;               // `let` can be reassigned
const LIMIT = compute(7);          // 7 is an argument, not the constant's value
const order = { quantity: 12 };    // object that is not a named constant
```

## Options

```js
"rule-pack/no-magic-numbers-in-business-logic": ["error", {
  allow: [-1, 0, 1],                    // replaces the default list
  constantPattern: "^[A-Z][A-Z0-9_]*$", // regex a constant's name must match
  ignoreArrayIndexes: true,
  ignoreDefaultParams: false,           // allow `function page(size = 25)`
}]
```

Partial options are merged with the defaults.
