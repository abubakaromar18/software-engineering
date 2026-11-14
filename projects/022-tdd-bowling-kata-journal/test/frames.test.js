import { describe, it, expect } from 'vitest';
import { buildFrames, isComplete } from '../src/index.js';

describe('buildFrames (step 6: extracted pure core)', () => {
  it('returns no frames for no rolls', () => {
    expect(buildFrames([])).toEqual([]);
  });

  it('classifies frames and computes running totals', () => {
    const frames = buildFrames([10, 7, 3, 9, 0]);
    expect(frames).toEqual([
      { number: 1, rolls: [10], kind: 'strike', score: 20, total: 20 },
      { number: 2, rolls: [7, 3], kind: 'spare', score: 19, total: 39 },
      { number: 3, rolls: [9, 0], kind: 'open', score: 9, total: 48 },
    ]);
  });

  it('marks a half-rolled frame as incomplete', () => {
    const [frame] = buildFrames([4]);
    expect(frame).toMatchObject({ kind: 'incomplete', score: null, total: null });
  });

  it('withholds a strike score until both bonus balls exist', () => {
    expect(buildFrames([10, 10]).map((f) => f.score)).toEqual([null, null]);
    expect(buildFrames([10, 10, 10])[0].score).toBe(30);
  });

  it('stops running totals at the first undecided frame', () => {
    // Frame 2 is a pending spare, frame 3 is decided on its own, but its
    // running total cannot be known yet.
    const frames = buildFrames([1, 1, 5, 5]);
    expect(frames.map((f) => f.total)).toEqual([2, null]);
  });

  it('reports completeness', () => {
    expect(isComplete(buildFrames(Array(20).fill(0)))).toBe(true);
    expect(isComplete(buildFrames(Array(19).fill(0)))).toBe(false);
    expect(isComplete(buildFrames(Array(11).fill(10)))).toBe(false);
  });

  it('does not mutate its input', () => {
    const rolls = Object.freeze([10, 5, 5, 3]);
    expect(() => buildFrames(rolls)).not.toThrow();
  });
});
