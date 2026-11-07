/**
 * Scripted walkthrough of the editor. Run with `npm run demo`.
 * Each step prints the buffer with `|` marking the cursor.
 */
import { Editor, transforms } from "./index.js";

const editor = new Editor("", { mergeWindowMs: Number.POSITIVE_INFINITY });

function show(step: string): void {
  const { text, cursor, dirty } = editor.state;
  const rendered = (text.slice(0, cursor) + "|" + text.slice(cursor)).replaceAll("\n", "⏎");
  console.log(`${step.padEnd(34)} ${JSON.stringify(rendered)}${dirty ? "  *" : ""}`);
}

// 1. Typing is coalesced word by word.
for (const ch of "hello brave world") editor.type(ch);
show("type 'hello brave world'");
console.log(`  undo stack: ${editor.undoLabels.join(" · ")}`);
editor.undo();
show("undo (removes one word)");
editor.redo();
show("redo");

// 2. Backspaces coalesce too.
editor.backspace();
editor.backspace();
show("backspace ×2");
editor.undo();
show("undo backspaces");
editor.markSaved();
show("save");

// 3. Macro: turn each line into a bullet.
editor.transform("Replace spaces", transforms.replaceAll(" ", "\n"));
show("split words onto lines");
editor.moveTo(0);
editor.startRecording("bulletize");
editor.moveToLineStart();
editor.type("- ");
editor.moveToNextLine();
const bulletize = editor.stopRecording();
show("record macro on line 1");
editor.playMacro(bulletize, 2);
show("play macro ×2 (one undo step)");
console.log(`  undo stack: ${editor.undoLabels.join(" · ")}`);

// 4. Memento checkpoints.
const checkpoint = editor.checkpoint("bullets");
editor.transform("Sort lines", transforms.sortLines);
editor.transform("Upper case", transforms.upperCase);
show("sort + upper case");
editor.restore(checkpoint);
show("restore checkpoint");
editor.undo();
show("undo the restore");

// 5. Walk all the way back to the save point.
while (editor.undoLabels.length > 0 && editor.state.dirty) editor.undo();
show("undo back to save point (clean)");
console.log(`  redo stack (next first): ${editor.redoLabels.join(" · ")}`);
