import { BowlingError } from './errors.js';
import { PINS } from './frames.js';

const SEPARATORS = /[\s|]/;

/**
 * Parses standard scoresheet notation into pin counts.
 *
 *   X  strike          /  spare (the rest of the rack)
 *   -  gutter (0)      0-9 pins knocked down
 *
 * Spaces and `|` are ignored, so "X|7/|9-" and "X 7/ 9-" are equivalent.
 * Only the notation itself is checked here; whether the resulting rolls form
 * a legal game is `buildFrames`' job.
 *
 * @param {string} text
 * @returns {number[]}
 */
export function parseNotation(text) {
  const rolls = [];

  for (const [index, char] of [...text].entries()) {
    if (SEPARATORS.test(char)) continue;

    const previous = rolls.at(-1);
    switch (char.toUpperCase()) {
      case 'X':
        rolls.push(PINS);
        break;
      case '-':
        rolls.push(0);
        break;
      case '/':
        if (previous === undefined || previous === PINS) {
          throw new BowlingError(`Position ${index + 1}: '/' must follow a non-strike ball`);
        }
        rolls.push(PINS - previous);
        break;
      default:
        if (!/^[0-9]$/.test(char)) {
          throw new BowlingError(`Position ${index + 1}: unexpected character '${char}'`);
        }
        rolls.push(Number(char));
    }
  }

  return rolls;
}
