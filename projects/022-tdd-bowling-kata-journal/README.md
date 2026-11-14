# TDD Bowling Kata Journal

A ten-pin bowling scorer in modern JavaScript, built strictly
**red → green → refactor** with [Vitest](https://vitest.dev). The code is
small; the point is the process. [`JOURNAL.md`](JOURNAL.md) records each of the
12 steps: the failing test, the minimum code that passed, and the refactor.

Beyond the classic `roll()`/`score()` kata it also:

- rejects impossible games (11 pins, 7 + 8 in one frame, a 22nd ball, bad fill balls)
- scores **partial** games, with running totals for frames that are already decided
- parses scoresheet notation (`X 7/ 9- …`) and prints an ASCII scorecard
- has a CLI

```text
$ node bin/bowling.js "X 7/ 9- X -8 8/ -6 X X X81"
+-----+-----+-----+-----+-----+-----+-----+-----+-----+-------+
|  1  |  2  |  3  |  4  |  5  |  6  |  7  |  8  |  9  |  10   |
+-----+-----+-----+-----+-----+-----+-----+-----+-----+-------+
|  X  | 7 / | 9 - |  X  | - 8 | 8 / | - 6 |  X  |  X  | X 8 1 |
|  20 |  39 |  48 |  66 |  74 |  84 |  90 | 120 | 148 |   167 |
+-----+-----+-----+-----+-----+-----+-----+-----+-----+-------+
Final score: 167

$ node bin/bowling.js "X X 7"        # frames 2–3 still waiting for balls
|  X  |  X  |  7  |     | ...
|  27 |     |     |     | ...
Game in progress

$ node bin/bowling.js 7 8
Error: Frame 1: 7 + 8 is more than 10 pins       # exit code 1
```

## Concepts and design decisions

| Concept | Where | Trade-off |
| --- | --- | --- |
| **Test-driven development** | `JOURNAL.md`, `test/*.test.js` | Every line of production code was demanded by a failing test. The design evolved (running sum → stored rolls → pure frame builder) instead of being guessed up front. It is slower at first, and some tests passed immediately; the journal says which. |
| **Tests as specification** | `describe('step N…')` blocks | Tests stay in the order they were written, so reading `game.test.js` top to bottom teaches the rules of bowling. |
| **Functional core, imperative shell** | `frames.js` (pure) vs `game.js`, `cli.js` | `buildFrames(rolls)` derives everything from the raw rolls. The class and CLI are thin wrappers. Rebuilding frames on every roll is O(n), which costs nothing for at most 21 balls and removes any chance of cached state drifting. |
| **Single source of truth for rules** | `BowlingGame.roll` validates via `buildFrames` | Validation and scoring cannot disagree because they are the same code. |
| **Atomic updates** | `roll()` builds a candidate list first | An illegal roll throws and leaves the game exactly as it was. |
| **Explicit "unknown"** | `score: null`, `total: null` | A strike waiting for bonus balls has no score yet. `null` says so; `NaN` or a partial number would lie. |
| **Domain error type** | `BowlingError` | The CLI catches only illegal-game errors and prints them; real bugs still crash with a stack trace. |
| **Layered parsing** | `notation.js` vs `frames.js` | The parser checks notation (`X/` is meaningless); `buildFrames` checks the game is legal. Each layer has one job. |
| **Testable I/O** | `run(args, io) → exitCode` | The CLI never touches `process` directly, so it is unit-tested without spawning a process. |
| **Table-driven and snapshot tests** | `it.each`, `toMatchInlineSnapshot` | Edge cases are one line each; the scorecard layout is reviewed in the test file itself. The table of marks is what caught the one real bug (step 11). |

## Architecture

```mermaid
flowchart LR
    CLI["bin/bowling.js → cli.run(args, io)"] --> N[parseNotation]
    N -->|number[]| F[buildFrames]
    G["BowlingGame.roll / score"] --> F
    F -->|Frame[]| S[renderScorecard / marksFor]
    S --> CLI
```

```text
src/
  errors.js     BowlingError
  frames.js     buildFrames, isComplete — all the rules (pure)
  game.js       BowlingGame — classic kata API
  notation.js   "X 7/ 9-" → [10, 7, 3, 9, 0]
  scorecard.js  frames → marks and ASCII table
  cli.js        argument handling, exit codes
  index.js      public exports
test/           one file per module; game.test.js follows the journal steps
```

## Build, run, test

Requires Node.js 18 or later.

```bash
npm install
npm test               # vitest run: 58 tests
npm run test:watch     # the red/green loop used to write it
npm start -- "XXXXXXXXXXXX"
```

As a library:

```js
import { BowlingGame } from './src/index.js';

const game = new BowlingGame();
[10, 7, 3, 9, 0].forEach((pins) => game.roll(pins));
game.frames().map((f) => f.total); // [20, 39, 48]
game.isOver;                       // false
game.score();                      // throws BowlingError: not final yet
```

## A note on the git history

The project brief asks for git history that documents each step. This
repository adds each project in a single commit, so `JOURNAL.md` records the
steps instead, with the code at each stage. Its last section explains how to
replay the kata as one commit per red/green/refactor step.

## Possible extensions

- Property-based tests (e.g. with `fast-check`): any legal game scores 0–300,
  and notation → rolls → marks round-trips.
- Mutation testing with Stryker to measure how strong the tests are.
- Multi-player games and a simple web scorecard on top of `buildFrames`.
- Alternative rule sets (candlepin, duckpin) by making the frame readers pluggable.
