import { BowlingError } from './errors.js';
import { buildFrames, isComplete } from './frames.js';

/**
 * The classic kata API: `roll(pins)` then `score()`.
 *
 * Every roll is validated by re-deriving the frames from the full roll list.
 * That is O(n) per roll, which is irrelevant for at most 21 balls, and it
 * means the game holds no derived state that could drift out of sync.
 */
export class BowlingGame {
  #rolls = [];

  /**
   * @param {number} pins
   * @throws {BowlingError} if the roll is illegal; the game is left unchanged.
   */
  roll(pins) {
    const candidate = [...this.#rolls, pins];
    buildFrames(candidate); // throws on an illegal roll before we commit it
    this.#rolls = candidate;
  }

  /** Final score. Only defined for a finished game. */
  score() {
    const frames = this.frames();
    if (!isComplete(frames)) {
      throw new BowlingError('Score is not final until all ten frames are complete');
    }
    return frames.at(-1).total;
  }

  /** Frames so far, with per-frame and running scores where known. */
  frames() {
    return buildFrames(this.#rolls);
  }

  get isOver() {
    return isComplete(this.frames());
  }

  /** A copy, so callers cannot mutate the game's history. */
  get rolls() {
    return [...this.#rolls];
  }
}
