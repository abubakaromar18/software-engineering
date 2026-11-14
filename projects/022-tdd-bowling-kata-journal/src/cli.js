import { BowlingError } from './errors.js';
import { buildFrames, isComplete } from './frames.js';
import { parseNotation } from './notation.js';
import { renderScorecard } from './scorecard.js';

const USAGE = `Usage: bowling <rolls>

Rolls use scoresheet notation: X strike, / spare, - gutter, 0-9 pins.
Spaces and | are ignored.

  bowling "X 7/ 9- X -8 8/ -6 X X X81"
  bowling XXXXXXXXXXXX`;

/**
 * CLI entry point, separated from process I/O so it can be unit tested.
 *
 * @param {string[]} args
 * @param {{ out: (s: string) => void, err: (s: string) => void }} io
 * @returns {number} process exit code
 */
export function run(args, io) {
  if (args.length === 0 || args.includes('-h') || args.includes('--help')) {
    io.out(USAGE);
    return args.length === 0 ? 2 : 0;
  }

  try {
    const frames = buildFrames(parseNotation(args.join(' ')));
    io.out(renderScorecard(frames));
    io.out(isComplete(frames)
      ? `Final score: ${frames.at(-1).total}`
      : 'Game in progress');
    return 0;
  } catch (error) {
    if (!(error instanceof BowlingError)) throw error;
    io.err(`Error: ${error.message}`);
    return 1;
  }
}
