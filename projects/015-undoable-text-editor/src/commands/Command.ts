import type { TextDocument } from "../document/TextDocument.js";

/**
 * The Command interface. Each command is a reified edit that can apply itself
 * to a document and reverse that application exactly.
 *
 * Contract:
 *  - `execute` followed by `undo` leaves the document (text AND cursor) exactly
 *    as it was before `execute`.
 *  - `execute` may be called again after `undo` (that is what redo does).
 *  - Commands throw before mutating anything if they cannot apply, so a failed
 *    command never leaves the document half-edited.
 */
export interface Command {
  /** Short description for history menus, e.g. `Type "hello"`. */
  readonly label: string;
  execute(document: TextDocument): void;
  undo(document: TextDocument): void;
  /**
   * Optional coalescing hook. If this command can absorb `next` (e.g. two
   * adjacent keystrokes), return the merged command; otherwise `undefined`.
   * Both commands have already been executed when this is called.
   */
  mergeWith?(next: Command): Command | undefined;
}
