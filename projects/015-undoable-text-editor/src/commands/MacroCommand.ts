import type { TextDocument } from "../document/TextDocument.js";
import type { Command } from "./Command.js";

/**
 * Composite command: a sequence of commands treated as one history entry.
 *
 * Execution is transactional. If child N throws, children N-1..0 are undone in
 * reverse order before the error propagates, so the document is untouched.
 */
export class MacroCommand implements Command {
  readonly #children: readonly Command[];

  constructor(
    readonly label: string,
    children: readonly Command[],
  ) {
    if (children.length === 0) {
      throw new TypeError("MacroCommand requires at least one child command.");
    }
    this.#children = [...children];
  }

  get size(): number {
    return this.#children.length;
  }

  execute(document: TextDocument): void {
    const done: Command[] = [];
    try {
      for (const child of this.#children) {
        child.execute(document);
        done.push(child);
      }
    } catch (error) {
      for (const child of done.reverse()) child.undo(document);
      throw error;
    }
  }

  undo(document: TextDocument): void {
    for (let i = this.#children.length - 1; i >= 0; i--) {
      this.#children[i]!.undo(document);
    }
  }
}
