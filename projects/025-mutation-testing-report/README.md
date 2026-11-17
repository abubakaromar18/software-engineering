# 025 · Mutation Testing Report

**invoice-kit** is a small TypeScript pricing library: integer-cents money, banker's rounding, quantity-tier discounts, coupons, and per-category sales tax. [Stryker](https://stryker-mutator.io/) mutation testing is set up on it, and the project records how the mutation score went from a **38% baseline to 100%**. Every test change in that journey was driven by a surviving mutant.

The library is the vehicle. The real subject is the gap between *"the tests run this code"* (coverage) and *"the tests would notice if this code were wrong"* (mutation score). The full write-up with before/after numbers is in **[MUTATION_REPORT.md](MUTATION_REPORT.md)**.

| Suite | Tests | Line coverage | Mutation score |
|---|---:|---:|---:|
| `test/baseline/` (frozen) | 14 | 83% | **38%** |
| `test/strengthened/` | 88 | 100% | **100%** (4 equivalent mutants on 2 lines documented and ignored) |

## What it demonstrates

- **Mutation testing as a test-quality metric.** Stryker rewrites the source in small ways (flips `>=` to `>`, deletes a block, swaps `+` for `-`, blanks a string) and re-runs the tests. If a mutant survives, nothing in the suite pins down that behaviour.
- **Two reproducible suites.** The weak baseline suite is kept frozen next to the strengthened one, each with its own Vitest and Stryker config. Anyone can re-run both and see the difference for themselves, without trusting a screenshot.
- **Killing mutants with intent.** Each test is added for a reason that can be named: boundary tests for `EqualityOperator` mutants, exact-value assertions for `ArithmeticOperator` mutants, error *codes* rather than bare `toThrow()` for `BlockStatement`/`ConditionalExpression` mutants, and whole-object `toEqual` on a hand-calculated invoice.
- **Mutation testing also improves the code.** One survivor showed that a sort tiebreaker was redundant, because `Array.prototype.sort` is stable. That line was deleted, not tested.
- **Equivalent mutants are handled honestly.** Mutants that no input can tell apart from the original are suppressed with scoped `// Stryker disable next-line` comments that give a reason. A blanket ignore would hide them.
- **Type-aware mutation.** `@stryker-mutator/typescript-checker` throws out mutants that would not compile (123 of 368) before any test runs, so time isn't spent on them and they don't inflate the score.
- **A CI gate.** `thresholds.break: 85` in `stryker.config.json` makes `npm run mutate` fail if the score regresses.
- **Domain correctness.** Money is held in integer cents and rounded half-to-even. Order-level coupons are split across lines with the largest-remainder method, so the line totals always add up to the invoice total.

## Architecture

```mermaid
flowchart LR
  L[LineInput[]] --> V[validate lines / tiers / tax table]
  V --> G[gross = unit × qty]
  G --> T[volume tier discount]
  T --> S[subtotal]
  S --> C{coupon applicable?}
  C -- yes --> D[coupon value, capped] --> A[allocate across lines<br/>largest remainder]
  C -- no --> R[record rejection<br/>or throw]
  A --> X[per-line tax by category<br/>half-even rounding]
  R --> X
  X --> I[Invoice]
```

```
src/
  money.ts      Money value object, roundHalfEven, allocate()
  discounts.ts  volume tiers, coupon applicability + value
  tax.ts        category tax table and per-line tax
  invoice.ts    the pipeline above; pure function calculateInvoice()
  errors.ts     InvoiceError with machine-readable codes
test/
  baseline/      the original "looks fine" suite (frozen)
  strengthened/  the suite after the mutation-driven rounds
stryker.config.json           strengthened run, break threshold 85
stryker.baseline.config.json  baseline run, no break threshold
```

### Design decisions and trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| Integer cents with explicit basis-point rates | No float drift, and the rounding happens in one place | Callers convert at the edges; currencies with 3 decimals would need a scale per currency |
| Banker's rounding (half-even) | Removes the upward bias of half-up rounding across many lines | Surprises people who expect `2.5 → 3`, so the tests document it |
| Coupon allocated per line before tax | Tax is computed on what is actually paid for each line, as most tax engines do | More complex than taxing the order once; `allocate()` must be exact |
| `invalidCoupon: "reject" \| "throw"` | Checkout UX wants "carry on and explain", APIs want "fail fast" | Two code paths to test |
| Only `InvoiceError` is downgraded to a rejection | A `TypeError` from bad input is a bug and must not be swallowed | Callers have to handle both error kinds |
| Frozen baseline suite kept in the repo | Makes the before/after reproducible | The repo carries a deliberately weak test file |
| `perTest` coverage analysis + TS checker | Each mutant runs only the tests that reach it, and uncompilable mutants are skipped | A full run takes about 5 minutes. Fine for nightly CI, slow for every pre-commit |

## Build, run, test

Requires Node 18+.

```bash
npm install
npm test                  # strengthened suite (88 tests)
npm run test:baseline     # baseline suite (14 tests)
npm run coverage          # v8 line/branch coverage
npm run typecheck
npm run example           # builds to dist/ and prints a worked invoice

npm run mutate            # Stryker on the strengthened suite, fails below 85%
npm run mutate:baseline   # Stryker on the baseline suite, for comparison
```

HTML and JSON reports go to `reports/mutation/` (git-ignored). Open `reports/mutation/strengthened.html` to browse each mutant in place.

## Example

```ts
import { calculateInvoice } from "invoice-kit";

const invoice = calculateInvoice(
  [
    { sku: "PEN-BLUE", unitPriceCents: 150, quantity: 20 },
    { sku: "NOTEBOOK", unitPriceCents: 499, quantity: 3, category: "reduced" },
    { sku: "APPLE", unitPriceCents: 80, quantity: 5, category: "food" },
  ],
  {
    issuedOn: "2026-11-17",
    tiers: [{ minQuantity: 10, basisPoints: 500 }, { minQuantity: 50, basisPoints: 1000 }],
    coupon: { code: "WELCOME10", kind: { type: "percent", basisPoints: 1000 }, minSpendCents: 1000 },
  },
);
```

`npm run example` output:

```
SKU        QTY  CAT            GROSS      VOLUME      COUPON         TAX       TOTAL
PEN-BLUE   20   standard    USD 30.00    USD 1.50    USD 2.85    USD 2.12   USD 27.77
NOTEBOOK   3    reduced     USD 14.97    USD 0.00    USD 1.50    USD 0.67   USD 14.14
APPLE      5    food         USD 4.00    USD 0.00    USD 0.40    USD 0.07    USD 3.67

Gross        USD 48.97
Volume        USD 1.50
Subtotal     USD 47.47
Coupon        USD 4.75  (WELCOME10)
Tax           USD 2.86
TOTAL        USD 45.58
```

Stryker's summary for the strengthened suite:

```
File          | % score | killed | survived | no cov | errors |
All files     |  100.00 |    245 |        0 |      0 |    123 |
```

## Possible extensions

- Turn on `incremental: true` and run only the mutants touched by a PR's diff, so mutation testing fits in a pre-merge check.
- Add property-based tests (fast-check) for `allocate` and `roundHalfEven`, and compare how many mutants they kill against the example-based tests.
- Per-currency minor-unit scale (JPY has 0 decimals, BHD has 3).
- Stack multiple coupons with a precedence policy, and add compound (tax-on-tax) jurisdictions.
- Publish the HTML report to the Stryker Dashboard and show a mutation-score badge.
