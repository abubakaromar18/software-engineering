import { BowlingError } from './errors.js';

export const PINS = 10;
export const FRAMES_PER_GAME = 10;

/**
 * @typedef {'strike' | 'spare' | 'open' | 'incomplete'} FrameKind
 *
 * @typedef {object} Frame
 * @property {number} number      1-based frame number.
 * @property {number[]} rolls     Pins knocked down by each ball in this frame.
 * @property {FrameKind} kind
 * @property {number | null} score Points for this frame, or null while bonus
 *                                 balls are still to be rolled.
 * @property {number | null} total Running total up to this frame, or null.
 */

/**
 * Turns a flat list of rolls into scored frames. This is the single source of
 * truth for the rules: the game object, the scorecard and the CLI all go
 * through it, so validation and scoring can never disagree.
 *
 * The function is pure. Partial games are fine: frames whose score depends on
 * balls not yet rolled get `score: null`.
 *
 * @param {readonly number[]} rolls
 * @returns {Frame[]}
 * @throws {BowlingError} when the rolls are not a legal (possibly partial) game.
 */
export function buildFrames(rolls) {
  rolls.forEach(assertValidPinCount);

  const frames = [];
  let cursor = 0;

  while (cursor < rolls.length) {
    const number = frames.length + 1;
    if (number > FRAMES_PER_GAME) {
      throw new BowlingError('Game is over: no more rolls allowed after the tenth frame');
    }
    const frame = number === FRAMES_PER_GAME
      ? readTenthFrame(rolls.slice(cursor))
      : readRegularFrame(rolls, cursor, number);
    frames.push(frame);
    cursor += frame.rolls.length;
  }

  return withRunningTotals(frames);
}

/** True when all ten frames are finished, fill balls included. */
export function isComplete(frames) {
  return frames.length === FRAMES_PER_GAME && frames.every((frame) => frame.score !== null);
}

function assertValidPinCount(pins, index) {
  if (!Number.isInteger(pins) || pins < 0 || pins > PINS) {
    throw new BowlingError(`Roll ${index + 1}: pins must be a whole number from 0 to ${PINS}, got ${pins}`);
  }
}

/** Frames 1–9: a strike takes one ball, otherwise two; bonuses look ahead. */
function readRegularFrame(rolls, start, number) {
  const first = rolls[start];

  if (first === PINS) {
    return frame(number, [first], 'strike', scoreWithBonus(rolls, start, 1, 2));
  }

  if (start + 1 >= rolls.length) {
    return frame(number, [first], 'incomplete', null);
  }

  const second = rolls[start + 1];
  if (first + second > PINS) {
    throw new BowlingError(`Frame ${number}: ${first} + ${second} is more than ${PINS} pins`);
  }

  return first + second === PINS
    ? frame(number, [first, second], 'spare', scoreWithBonus(rolls, start, 2, 1))
    : frame(number, [first, second], 'open', first + second);
}

/**
 * Frame 10: no look-ahead. A strike or spare earns fill balls inside the
 * frame itself, and the pins are reset whenever the rack is cleared.
 */
function readTenthFrame(rolls) {
  if (rolls.length > 3) {
    throw new BowlingError('Game is over: no more rolls allowed after the tenth frame');
  }

  const [first, second, third] = rolls;
  const number = FRAMES_PER_GAME;

  if (second !== undefined && first < PINS && first + second > PINS) {
    throw new BowlingError(`Frame ${number}: ${first} + ${second} is more than ${PINS} pins`);
  }

  const earnedFillBall = second !== undefined && first + second >= PINS;
  if (third !== undefined) {
    if (!earnedFillBall) {
      throw new BowlingError('Game is over: an open tenth frame has no fill ball');
    }
    // After a strike followed by a non-strike, the second and third balls
    // share one rack of pins.
    if (first === PINS && second < PINS && second + third > PINS) {
      throw new BowlingError(`Frame ${number}: fill balls ${second} + ${third} are more than ${PINS} pins`);
    }
  }

  const needed = earnedFillBall || first === PINS ? 3 : 2;
  if (rolls.length < needed) {
    return frame(number, [...rolls], 'incomplete', null);
  }

  const kind = first === PINS ? 'strike' : earnedFillBall ? 'spare' : 'open';
  return frame(number, [...rolls], kind, rolls.reduce(sum, 0));
}

/**
 * Score for a strike or spare: the frame's own balls plus the next
 * `bonusCount` balls, or null if those have not been rolled yet.
 */
function scoreWithBonus(rolls, start, ownCount, bonusCount) {
  const end = start + ownCount + bonusCount;
  if (end > rolls.length) return null;
  return rolls.slice(start, end).reduce(sum, 0);
}

function withRunningTotals(frames) {
  let total = 0;
  let known = true;
  return frames.map((f) => {
    known = known && f.score !== null;
    total += f.score ?? 0;
    return { ...f, total: known ? total : null };
  });
}

function frame(number, rolls, kind, score) {
  return { number, rolls, kind, score, total: null };
}

function sum(a, b) {
  return a + b;
}
