import type { Command } from "../commands/Command.js";
import type { TextDocument } from "../document/TextDocument.js";

/**
 * A recorded step is a *factory* rather than a concrete command: positions are
 * resolved against the document at playback time. That is what lets a macro
 * recorded at offset 0 be replayed later at the cursor, wherever it is.
 */
export type CommandFactory = (document: TextDocument) => Command | undefined;

export interface Macro {
  readonly name: string;
  readonly steps: readonly CommandFactory[];
}

/** Collects command factories while recording is active. */
export class MacroRecorder {
  #name: string | undefined;
  #steps: CommandFactory[] = [];

  get isRecording(): boolean {
    return this.#name !== undefined;
  }

  start(name: string): void {
    if (this.isRecording) throw new Error(`Already recording macro "${this.#name}".`);
    if (name.trim().length === 0) throw new TypeError("Macro name must not be empty.");
    this.#name = name;
    this.#steps = [];
  }

  record(step: CommandFactory): void {
    if (this.isRecording) this.#steps.push(step);
  }

  stop(): Macro {
    if (this.#name === undefined) throw new Error("Not recording a macro.");
    const macro: Macro = Object.freeze({ name: this.#name, steps: Object.freeze([...this.#steps]) });
    this.#name = undefined;
    this.#steps = [];
    return macro;
  }
}
