# Mutation Testing Report: invoice-kit

Tool: Stryker 8.7 (`@stryker-mutator/vitest-runner`, `@stryker-mutator/typescript-checker`), `coverageAnalysis: perTest`.
Scope: every file in `src/` except the `index.ts` barrel. Final source: 368 mutants generated.

## Summary

| Run | Source | Tests | Line cov. | Killed | Survived | No coverage | Compile errors | Ignored | **Score** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | final | 14 | 83.1% | 94 | 103 | 48 | 123 | 4 | **38.37%** |
| Round 1 | pre-cleanup* | 88 | 100% | 244 | 7 | 0 | 125 | 0 | **97.21%** |
| Round 2 (final) | final | 88 | 100% | 245 | 0 | 0 | 123 | 4 | **100.00%** |

\* Round 1 ran before the redundant tiebreaker was removed in Round 2. That source had 376 mutants, 8 more than the final 368. The baseline row was re-run against the final source, so rows 1 and 3 compare like with like.

Score = killed ÷ (killed + survived + no coverage). Compile errors are mutants the TypeScript checker rejected before any test ran. They count neither for nor against the score.

To reproduce: `npm run mutate:baseline` and `npm run mutate`.

## Baseline: what 83% coverage was hiding

The baseline suite is typical of real code that has passed review. Every module is exercised and every test is green. Its weakness is in the assertions:

```ts
expect(a.subtract(b).cents).toBeGreaterThan(0);   // passes for + as well as -
expect(Money.of(1234).format()).toContain("12");   // passes for "USD 12.34" and "USD 0.12"
expect(selectTier(tiers, 60)).toBeDefined();        // passes for the wrong tier
expect(() => Money.of(1.5)).toThrow();              // passes for any error at all
expect(invoice.total.cents).toBeGreaterThan(0);     // passes for almost any total
```

The 151 baseline mutants that were not killed (103 survived, 48 never covered), by Stryker mutator:

| Mutator | Not killed | What it tells you |
|---|---:|---|
| ConditionalExpression | 46 | Guards like `if (!Number.isInteger(q))` could be replaced with `false` and nothing noticed. Input validation was effectively untested |
| StringLiteral | 27 | Error messages (and `"-"` in `format()`) are never checked |
| BlockStatement | 26 | Whole `throw` blocks could be deleted, mostly in code no test reached |
| EqualityOperator | 23 | No test sits exactly on a boundary: `>=` vs `>` on tier thresholds, coupon dates, min spend, the 0..10000 rate limits |
| ArithmeticOperator | 13 | `allocate()` maths and `format()` could be wrong, because only `toHaveLength` was checked |
| LogicalOperator | 8 | `a \|\| b` → `a && b` in validators, because only one side was ever false |
| MethodExpression / Regex / other | 8 | `trim()` removal, loosened ISO-date regex anchors |

Representative baseline survivors (file:line → mutant):

| Location | Mutant | Why it survived |
|---|---|---|
| `money.ts:43` | `this.cents - other.cents` → `+` | Only asserted `> 0` |
| `money.ts:65` | `<=` → `<` in `min()` | Equal amounts never compared |
| `money.ts:116` | sign `"-"` → `""` | Negative amounts never formatted |
| `discounts.ts:36` | `quantity >= minQuantity` → `>` | Quantity 60 is far from both thresholds |
| `discounts.ts:70,73` | `onDate < validFrom` → `<=`, `>` → `>=` | No test on the first or last valid day |
| `discounts.ts:76` | `subtotal < minSpend` → `<=` | No test at exactly the minimum spend |
| `tax.ts:32` | negative-base clamp → `false` | Never called with a negative base |
| `invoice.ts` regex | `^\d{4}…$` → anchors removed | Invalid dates never tried |

## Round 1: strengthening by mutator category

The survivor list was worked through by category rather than one mutant at a time, so that each kind of weakness got one consistent fix:

1. **Exact values instead of loose ones** (ArithmeticOperator, StringLiteral in `format`). Every arithmetic result is asserted with `toBe(n)`. `format()` gets a table of exact strings covering zero, sub-dollar and negative amounts.
2. **Boundary triples** (EqualityOperator). For every comparison there are tests just below, exactly on and just above the boundary: tier thresholds 9/10/49/50, the coupon window's day before, first day, last day and day after, min spend 1999/2000, rates −1/0/10000/10001.
3. **Error codes, not bare `toThrow()`** (ConditionalExpression, BlockStatement). A helper asserts `instanceof InvoiceError` and the specific `code`. A mutant that removes one guard is caught even when a later guard would also throw.
4. **Each side of every `||`** (LogicalOperator). Every validator gets one failing input per clause (e.g. zero *and* fractional `minQuantity`).
5. **One hand-calculated invoice compared whole** (everything in `invoice.ts`). A `summary()` helper flattens the invoice to cents and the test uses a single `toEqual`, so no field can drift unnoticed. The arithmetic is written out in a comment above it.
6. **Invariants as well as examples.** `allocate()` must sum back to the original for six amounts. Line totals must reconcile with the invoice total.

Result: **97.21%**, 7 survivors.

## Round 2: the last seven

| # | Location | Mutant | Resolution |
|---|---|---|---|
| 1–3 | `discounts.ts` coupon errors | message → `""` | **Test added.** Assert the message text with `toThrow("must not be blank")` etc. Callers show these messages, so they are behaviour |
| 4 | `invoice.ts` issuedOn error | template → `` `` `` | **Test added.** Assert the message includes the rejected value |
| 5 | `money.ts` `allocate` sort | `a.index - b.index` → `+` | **Code changed.** The tiebreaker was dead: `Array.prototype.sort` is stable (ES2019) and the input is already in index order, so ties keep it. The tiebreaker was deleted and a comment now explains why ordering stays deterministic. Tests for the tie case (`100 / [1,1,1]` → `[34,33,33]`) remain |
| 6–7 | `money.ts` `roundHalfEven` | `diff > 0.5 + ε` → `>=`, `diff < 0.5 − ε` → `<=` | **Equivalent mutant, ignored.** These differ only when `diff` is *exactly* `0.5 ± 1e-9`. `(cents × bp) / 10000` cannot produce that value, so no test can observe the difference. Each line has `// Stryker disable next-line EqualityOperator: <reason>`. That suppresses 2 mutants per line (4 shown as *Ignored*) |

Result: **100%** on 368 mutants (245 killed, 123 compile errors, 4 ignored).

## Lessons

- **Coverage measures execution, mutation score measures verification.** The baseline executed 83% of lines but checked only 38% of behaviour. Branch coverage (73%) was a better hint than line coverage, but it still overstated how good the suite was.
- **Mutants cluster.** Most baseline survivors traced back to two habits: loose assertions and bare `toThrow()`. Fixing those habits once killed far more mutants than writing a test for each mutant would have.
- **Sometimes a survivor means the code should change, not the tests.** Mutant 5 found dead logic. Testing it would have locked in code that does nothing.
- **Suppress mutants narrowly and give a reason.** Scoped `disable next-line <Mutator>: reason` comments keep the ignore list honest and easy to review. Excluding whole files or mutators would hide real gaps.
- **The type checker matters in TypeScript.** A third of the generated mutants (123/368) don't compile. Without the checker each one would cost a test run and show up as a confusing runtime error.
- **Cost.** A full run takes about 5½ minutes against about 0.4 s for the unit tests. Run it nightly, or with `incremental` on changed files in PRs, rather than on every save.

## Keeping it at 100%

`stryker.config.json` sets `thresholds.break: 85`, so `npm run mutate` exits non-zero if the score falls below 85%. The threshold sits below 100% on purpose. A gate at 100% pushes people to write assertion-only tests that kill mutants without checking useful behaviour.
