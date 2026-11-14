import { describe, it, expect } from 'vitest';
import { parseNotation, BowlingError } from '../src/index.js';

describe('parseNotation (step 10)', () => {
  it('parses strikes, spares, gutters and digits', () => {
    expect(parseNotation('X 7/ 9- -8')).toEqual([10, 7, 3, 9, 0, 0, 8]);
  });

  it('ignores spaces and frame separators', () => {
    expect(parseNotation('X|7/|9-')).toEqual(parseNotation('X7/9-'));
  });

  it('accepts a lowercase x', () => {
    expect(parseNotation('xx')).toEqual([10, 10]);
  });

  it('parses a spare in the tenth frame after a strike', () => {
    expect(parseNotation('X7/')).toEqual([10, 7, 3]);
  });

  it.each(['/', 'X/', '5A'])('rejects %j', (text) => {
    expect(() => parseNotation(text)).toThrow(BowlingError);
  });
});
