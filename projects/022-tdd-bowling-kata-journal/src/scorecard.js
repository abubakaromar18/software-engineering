import { PINS, FRAMES_PER_GAME } from './frames.js';

const REGULAR_WIDTH = 5;
const TENTH_WIDTH = 7;

/**
 * Display marks for one frame, e.g. [10] → ['X'] and [7, 3] → ['7', '/'].
 * The tenth frame is special because the rack resets after a strike or spare.
 *
 * @param {import('./frames.js').Frame} frame
 * @returns {string[]}
 */
export function marksFor(frame) {
  const marks = [];
  let standing = PINS;
  let freshRack = true;

  for (const pins of frame.rolls) {
    if (freshRack && pins === PINS) {
      marks.push('X');
    } else if (!freshRack && pins === standing) {
      marks.push('/');
    } else {
      marks.push(pins === 0 ? '-' : String(pins));
    }

    // A rack is reset once cleared or after its second ball. Only the tenth
    // frame ever has a ball after that, which is what makes it special.
    standing -= pins;
    if (standing === 0 || !freshRack) {
      standing = PINS;
      freshRack = true;
    } else {
      freshRack = false;
    }
  }

  return marks;
}

/**
 * Renders frames as a three-row ASCII scorecard. Unplayed frames are blank.
 *
 * @param {import('./frames.js').Frame[]} frames
 * @returns {string}
 */
export function renderScorecard(frames) {
  const cells = Array.from({ length: FRAMES_PER_GAME }, (_, i) => {
    const frame = frames[i];
    const width = i === FRAMES_PER_GAME - 1 ? TENTH_WIDTH : REGULAR_WIDTH;
    return {
      width,
      header: center(String(i + 1), width),
      marks: center(frame ? marksFor(frame).join(' ') : '', width),
      total: frame?.total == null ? ' '.repeat(width) : String(frame.total).padStart(width - 1) + ' ',
    };
  });

  const row = (key) => `|${cells.map((c) => c[key]).join('|')}|`;
  const rule = `+${cells.map((c) => '-'.repeat(c.width)).join('+')}+`;
  return [rule, row('header'), rule, row('marks'), row('total'), rule].join('\n');
}

function center(text, width) {
  const left = Math.floor((width - text.length) / 2);
  return ' '.repeat(left) + text + ' '.repeat(width - text.length - left);
}
