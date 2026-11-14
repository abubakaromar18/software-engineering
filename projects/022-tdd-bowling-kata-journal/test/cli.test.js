import { describe, it, expect } from 'vitest';
import { run } from '../src/cli.js';

function capture(args) {
  const out = [];
  const err = [];
  const code = run(args, { out: (s) => out.push(s), err: (s) => err.push(s) });
  return { code, out: out.join('\n'), err: err.join('\n') };
}

describe('cli (step 12)', () => {
  it('prints a scorecard and the final score', () => {
    const result = capture(['XXXXXXXXXXXX']);
    expect(result.code).toBe(0);
    expect(result.out).toContain('Final score: 300');
  });

  it('joins multiple arguments', () => {
    expect(capture(['X', '7/', '9-']).out).toContain('Game in progress');
  });

  it('reports illegal games on stderr with exit code 1', () => {
    const result = capture(['78']);
    expect(result.code).toBe(1);
    expect(result.err).toMatch(/^Error: Frame 1: 7 \+ 8/);
  });

  it('prints usage with no arguments', () => {
    const result = capture([]);
    expect(result.code).toBe(2);
    expect(result.out).toMatch(/^Usage/);
  });

  it('prints usage for --help and succeeds', () => {
    expect(capture(['--help']).code).toBe(0);
  });
});
