import { describe, it, expect } from 'vitest';
import { buildFrames, marksFor, renderScorecard, parseNotation } from '../src/index.js';

const framesOf = (text) => buildFrames(parseNotation(text));

describe('marksFor (step 11)', () => {
  it.each([
    [[10], ['X']],
    [[7, 3], ['7', '/']],
    [[0, 8], ['-', '8']],
    [[0, 10], ['-', '/']],
    [[10, 10, 10], ['X', 'X', 'X']],
    [[10, 7, 3], ['X', '7', '/']],
    [[10, 0, 10], ['X', '-', '/']],
    [[8, 2, 10], ['8', '/', 'X']],
  ])('%j → %j', (rolls, expected) => {
    expect(marksFor({ rolls })).toEqual(expected);
  });

  it('round-trips through the notation parser', () => {
    const text = 'X 7/ 9- X -8 8/ -6 X X X81';
    const marks = framesOf(text).map((f) => marksFor(f).join('')).join(' ');
    expect(marks).toBe(text);
  });
});

describe('renderScorecard (step 11)', () => {
  it('renders a finished game', () => {
    expect(renderScorecard(framesOf('X 7/ 9- X -8 8/ -6 X X X81'))).toMatchInlineSnapshot(`
      "+-----+-----+-----+-----+-----+-----+-----+-----+-----+-------+
      |  1  |  2  |  3  |  4  |  5  |  6  |  7  |  8  |  9  |  10   |
      +-----+-----+-----+-----+-----+-----+-----+-----+-----+-------+
      |  X  | 7 / | 9 - |  X  | - 8 | 8 / | - 6 |  X  |  X  | X 8 1 |
      |  20 |  39 |  48 |  66 |  74 |  84 |  90 | 120 | 148 |   167 |
      +-----+-----+-----+-----+-----+-----+-----+-----+-----+-------+"
    `);
  });

  it('leaves unplayed frames and undecided totals blank', () => {
    const lines = renderScorecard(framesOf('3 4 X')).split('\n');
    expect(lines[3]).toBe('| 3 4 |  X  |     |     |     |     |     |     |     |       |');
    expect(lines[4]).toBe('|   7 |     |     |     |     |     |     |     |     |       |');
  });
});
