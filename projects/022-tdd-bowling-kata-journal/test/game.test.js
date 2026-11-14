import { describe, it, expect, beforeEach } from 'vitest';
import { BowlingGame, BowlingError } from '../src/index.js';

// Tests are kept in the order they were written; each `describe` block maps to
// a step in JOURNAL.md.

let game;

beforeEach(() => {
  game = new BowlingGame();
});

function rollMany(times, pins) {
  for (let i = 0; i < times; i++) game.roll(pins);
}

function rollAll(rolls) {
  rolls.forEach((pins) => game.roll(pins));
}

describe('step 1–2: open frames', () => {
  it('scores a gutter game as 0', () => {
    rollMany(20, 0);
    expect(game.score()).toBe(0);
  });

  it('scores all ones as 20', () => {
    rollMany(20, 1);
    expect(game.score()).toBe(20);
  });
});

describe('step 3: spares', () => {
  it('adds the next ball as a spare bonus', () => {
    rollAll([5, 5, 3]);
    rollMany(17, 0);
    expect(game.score()).toBe(16);
  });

  it('does not treat 10 pins split across two frames as a spare', () => {
    rollAll([3, 5, 5, 3]);
    rollMany(16, 0);
    expect(game.score()).toBe(16);
  });
});

describe('step 4: strikes', () => {
  it('adds the next two balls as a strike bonus', () => {
    rollAll([10, 3, 4]);
    rollMany(16, 0);
    expect(game.score()).toBe(24);
  });

  it('handles consecutive strikes (a "double")', () => {
    rollAll([10, 10, 4, 2]);
    rollMany(14, 0);
    expect(game.score()).toBe(24 + 16 + 6);
  });
});

describe('step 5: tenth frame', () => {
  it('scores a perfect game as 300', () => {
    rollMany(12, 10);
    expect(game.score()).toBe(300);
  });

  it('scores all spares with a final fill ball', () => {
    rollMany(21, 5);
    expect(game.score()).toBe(150);
  });

  it('scores a spare then a strike in the tenth frame', () => {
    rollMany(18, 0);
    rollAll([7, 3, 10]);
    expect(game.score()).toBe(20);
  });

  it('scores a strike then two fill balls in the tenth frame', () => {
    rollMany(18, 0);
    rollAll([10, 7, 3]);
    expect(game.score()).toBe(20);
  });

  it('scores a well-known sample game', () => {
    // X 7/ 9- X -8 8/ -6 X X X81
    rollAll([10, 7, 3, 9, 0, 10, 0, 8, 8, 2, 0, 6, 10, 10, 10, 8, 1]);
    expect(game.score()).toBe(167);
  });
});

describe('step 7: rejecting impossible pin counts', () => {
  it.each([-1, 11, 2.5, NaN, '5'])('rejects %s pins', (pins) => {
    expect(() => game.roll(pins)).toThrow(BowlingError);
  });

  it('rejects two balls totalling more than 10 in one frame', () => {
    game.roll(7);
    expect(() => game.roll(4)).toThrow(/more than 10 pins/);
  });

  it('leaves the game unchanged after an illegal roll', () => {
    game.roll(7);
    expect(() => game.roll(4)).toThrow();
    game.roll(3);
    expect(game.rolls).toEqual([7, 3]);
  });
});

describe('step 8: game over', () => {
  it('rejects a roll after a complete open game', () => {
    rollMany(20, 0);
    expect(game.isOver).toBe(true);
    expect(() => game.roll(0)).toThrow(/Game is over/);
  });

  it('rejects a roll after the fill balls', () => {
    rollMany(12, 10);
    expect(() => game.roll(0)).toThrow(/Game is over/);
  });

  it('rejects a third ball in an open tenth frame', () => {
    rollMany(18, 0);
    rollAll([3, 4]);
    expect(() => game.roll(1)).toThrow(/no fill ball/);
  });

  it('rejects fill balls that knock down more than one rack', () => {
    rollMany(18, 0);
    rollAll([10, 6]);
    expect(() => game.roll(5)).toThrow(/fill balls/);
  });

  it('allows a strike on the third ball after a strike and a strike', () => {
    rollMany(18, 0);
    rollAll([10, 10, 10]);
    expect(game.score()).toBe(30);
  });

  it('allows a strike on the third ball after a spare', () => {
    rollMany(18, 0);
    rollAll([4, 6, 10]);
    expect(game.score()).toBe(20);
  });
});

describe('step 9: incomplete games', () => {
  it('refuses to report a final score before the game ends', () => {
    rollMany(19, 0);
    expect(() => game.score()).toThrow(/not final/);
  });

  it('refuses a final score while fill balls are owed', () => {
    rollMany(18, 0);
    rollAll([10, 10]);
    expect(game.isOver).toBe(false);
    expect(() => game.score()).toThrow(BowlingError);
  });

  it('exposes running totals for frames that are already decided', () => {
    rollAll([3, 4, 10, 5]);
    expect(game.frames().map((f) => f.total)).toEqual([7, null, null]);
  });

  it('returns a defensive copy of the rolls', () => {
    game.roll(3);
    game.rolls.push(99);
    expect(game.rolls).toEqual([3]);
  });
});
