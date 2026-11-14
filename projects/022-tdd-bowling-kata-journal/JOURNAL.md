# TDD Journal

This is the step-by-step record of building the scorer red → green → refactor.
Each step names the failing test written first (**Red**), the smallest change
that made it pass (**Green**), and the clean-up done with all tests green
(**Refactor**). Test names match the `describe('step N…')` blocks in `test/`.

> This repository adds each project as one commit, so the per-step git
> history is reproduced here rather than as separate commits. See
> [Replaying the kata](#replaying-the-kata) for a way to rebuild it as real
> commits.

---

## Step 1 — Gutter game

**Red.** `scores a gutter game as 0`: `new BowlingGame()` does not exist.

**Green.**

```js
class BowlingGame { roll() {} score() { return 0; } }
```

Returning a constant is deliberate: the test does not yet demand more.

**Refactor.** Nothing yet. Added the `rollMany(times, pins)` test helper
because the next test needs it too.

## Step 2 — All ones

**Red.** `scores all ones as 20` fails with `expected 0 to be 20`.

**Green.** Keep a running sum: `roll(p) { this.total += p }`.

**Refactor.** None. The obvious next test will break this design, and it is
better to let the test drive that change than to guess.

## Step 3 — One spare

**Red.** `adds the next ball as a spare bonus`: 5, 5, 3 should score 16, the
running sum gives 13.

**Green.** A running sum cannot look ahead. Store the rolls instead and score
in `score()`, walking two balls at a time:

```js
for (let frame = 0, i = 0; frame < 10; frame++, i += 2) {
  if (rolls[i] + rolls[i + 1] === 10) total += 10 + rolls[i + 2];
  else total += rolls[i] + rolls[i + 1];
}
```

**Refactor.** Wrote a second test (`does not treat 10 pins split across two
frames as a spare`) to pin down that a spare is decided *per frame*, not per
adjacent pair. It passed immediately, which confirmed the frame-walking loop.

## Step 4 — One strike

**Red.** `adds the next two balls as a strike bonus`: 10, 3, 4 should be 24.

**Green.** A strike frame is one ball, so the cursor advances by one:

```js
if (rolls[i] === 10) { total += 10 + rolls[i + 1] + rolls[i + 2]; i += 1; }
```

**Refactor.** Extracted `isStrike`, `isSpare`, `strikeBonus`, `spareBonus`.
The loop now reads like the rulebook. Added the double-strike test as a
regression guard.

## Step 5 — Tenth frame and perfect game

**Red.** `scores a perfect game as 300` *passed straight away*: the loop stops
after ten frames, so the two fill balls are counted only as bonuses. That is
a useful surprise: the tenth frame needed no special handling for *scoring*.
The tests for 7/X, X73 and the 167 sample game passed too.

**Green.** Nothing to change.

**Refactor.** None. The tenth frame becomes special only once validation
arrives (step 8).

## Step 6 — Extract the pure core

No new behaviour, so no Red. With 9 green tests, the scoring loop moved out
of the class into a pure function, `buildFrames(rolls) → Frame[]`, that
returns each frame's rolls, kind, score and running total.

Why: the upcoming steps (validation, partial games, a scorecard) all need to
*see frames*, not just a total. One function that derives everything from the
raw rolls means the class keeps no derived state that could drift. The class
became a thin wrapper, and `test/frames.test.js` started here.

## Step 7 — Impossible pin counts

**Red.** `rejects 11 pins` (and -1, 2.5, NaN, `'5'`): nothing threw.

**Green.** `assertValidPinCount` at the top of `buildFrames`, throwing a new
`BowlingError`.

**Red.** `rejects two balls totalling more than 10 in one frame`.

**Green.** Check `first + second > 10` when reading a regular frame.

**Red.** `leaves the game unchanged after an illegal roll`: the bad roll had
already been pushed.

**Green → Refactor.** `roll()` now builds a *candidate* roll list, validates
it with `buildFrames`, and only then commits it. Validation and scoring share
one code path, so they cannot disagree.

## Step 8 — Game over and the real tenth frame

**Red.** `rejects a roll after a complete open game`: a 21st ball was
silently ignored by the frame loop.

**Green.** Throw when rolls remain after frame ten.

**Red.** `rejects a third ball in an open tenth frame`, then `rejects fill
balls that knock down more than one rack` (X, 6, 5).

**Green.** This is where the tenth frame finally earned its own reader,
`readTenthFrame`, which knows that a strike or spare earns fill balls and that
the rack resets only when it is cleared.

**Refactor.** Added the X-X-X and 4-6-X tests to prove the reset rule allows
what it should, not just forbids what it should.

## Step 9 — Incomplete games

**Red.** `refuses to report a final score before the game ends`: `score()`
returned `NaN` for 19 balls (an `undefined` bonus).

**Green.** Frames whose bonus balls have not been rolled get `score: null`;
running totals stop at the first unknown frame; `score()` throws until
`isComplete`.

**Refactor.** `null` instead of `NaN` or a partial number makes "not known
yet" explicit. Exposed `frames()` and `isOver` so a UI can show progress.
Made `rolls` a defensive copy.

## Step 10 — Scoresheet notation

**Red.** `parseNotation('X 7/ 9- -8')` did not exist.

**Green.** A character loop: `X`→10, `-`→0, digit→n, `/`→10 − previous ball.

**Refactor.** Decided the parser checks *notation only* (e.g. `X/` is
nonsense notation) and leaves game legality to `buildFrames`. Two layers,
one responsibility each.

## Step 11 — Scorecard

**Red.** `marksFor` and `renderScorecard` did not exist.

**Green.** Marks per frame and a fixed-width table; the full sample game is
an inline snapshot.

**Red (a real bug).** `[10, 0, 10] → X - /` came out as `X - X`. The first
version decided "is this ball on a fresh rack?" by checking whether ten pins
were standing, which is also true after a gutter ball.

**Green.** Track the rack explicitly: a rack is fresh until its first ball,
and resets after it is cleared or after its second ball. `[0, 10] → - /`
was added as a sharper, smaller regression test.

**Refactor.** Added the round-trip test: notation → frames → marks gives the
original notation back.

## Step 12 — CLI

**Red.** `run(['XXXXXXXXXXXX'], io)` did not exist.

**Green.** `src/cli.js` takes args and an `io` object and returns an exit
code; `bin/bowling.js` is a three-line adapter to `process`.

**Refactor.** Only `BowlingError` is caught and printed; anything else is a
bug and is allowed to crash with a stack trace.

---

## What TDD changed in the design

- **The state model changed twice, each time because a test forced it**: a
  running sum (step 2), then stored rolls (step 3), then a pure frame
  builder (step 6). Designing up front would likely have skipped step 2, but
  might also have over-built a `Frame` class hierarchy that the tests never
  asked for.
- **Some tests passed first time** (steps 3b, 5). That is fine. They document
  behaviour and guard against regressions, but they did not drive code, so
  they are noted as such.
- **The one real bug was in display code**, where the tests were thinnest at
  first. A table-driven test with edge cases (`it.each`) found it.

## Replaying the kata

To rebuild the history as real commits in a scratch repo, do each step in
order: copy in only that step's tests, watch them fail (`npm test`), write the
smallest code that passes, then commit with a message like
`step 3: green - spare bonus`.
