import { describe, expect, it, vi } from "vitest";
import { Editor, transforms, type EditorState } from "../src/index.js";

const newEditor = (text = "") => new Editor(text, { mergeWindowMs: Number.POSITIVE_INFINITY });
const typeEach = (editor: Editor, text: string) => {
  for (const ch of text) editor.type(ch);
};

describe("Editor editing and undo", () => {
  it("undoes typing one word at a time", () => {
    const editor = newEditor();
    typeEach(editor, "the quick fox");
    expect(editor.undoLabels).toEqual(['Type "the "', 'Type "quick "', 'Type "fox"']);
    editor.undo();
    expect(editor.text).toBe("the quick ");
    editor.undo();
    editor.undo();
    expect(editor.text).toBe("");
    expect(editor.undo()).toBe(false);
  });

  it("coalesces backspaces and restores the cursor on undo", () => {
    const editor = newEditor("hello");
    editor.backspace();
    editor.backspace();
    expect(editor.text).toBe("hel");
    expect(editor.undoLabels).toEqual(['Delete "lo"']);
    editor.undo();
    expect(editor.state).toMatchObject({ text: "hello", cursor: 5 });
  });

  it("ignores backspace at the start and empty typing", () => {
    const editor = newEditor("x");
    editor.moveTo(0);
    editor.backspace();
    editor.type("");
    expect(editor.state.canUndo).toBe(false);
  });

  it("starts a new undo group after a cursor jump", () => {
    const editor = newEditor();
    typeEach(editor, "ab");
    editor.moveTo(0);
    typeEach(editor, "xy");
    expect(editor.text).toBe("xyab");
    expect(editor.undoLabels).toEqual(['Type "ab"', 'Type "xy"']);
  });

  it("makes whole-document transforms a single undo step", () => {
    const editor = newEditor("b\na\nc");
    editor.transform("Sort lines", transforms.sortLines);
    expect(editor.text).toBe("a\nb\nc");
    editor.undo();
    expect(editor.text).toBe("b\na\nc");
    editor.redo();
    expect(editor.text).toBe("a\nb\nc");
  });

  it("supports explicit range deletion", () => {
    const editor = newEditor("abcdef");
    editor.deleteRange(1, 3);
    expect(editor.text).toBe("adef");
    editor.undo();
    expect(editor.text).toBe("abcdef");
  });
});

describe("Editor macros", () => {
  function recordBulletMacro(editor: Editor) {
    editor.startRecording("bullet");
    editor.moveToLineStart();
    editor.type("- ");
    editor.moveToNextLine();
    return editor.stopRecording();
  }

  it("records relative steps and replays them at the current position", () => {
    const editor = newEditor("one\ntwo\nthree");
    editor.moveTo(0);
    const macro = recordBulletMacro(editor);
    expect(editor.text).toBe("- one\ntwo\nthree");
    editor.playMacro(macro, 2);
    expect(editor.text).toBe("- one\n- two\n- three");
  });

  it("undoes an entire macro playback in one step, restoring the cursor", () => {
    const editor = newEditor("one\ntwo\nthree");
    editor.moveTo(0);
    const macro = recordBulletMacro(editor);
    const before = editor.state;
    editor.playMacro(macro, 2);
    expect(editor.undoLabels.at(-1)).toBe('Macro "bullet" ×2');
    editor.undo();
    expect(editor.state).toMatchObject({ text: before.text, cursor: before.cursor });
    editor.redo();
    expect(editor.text).toBe("- one\n- two\n- three");
  });

  it("leaves the document untouched when a macro step fails", () => {
    const editor = newEditor("abc");
    editor.startRecording("delete-range");
    editor.deleteRange(0, 2);
    const macro = editor.stopRecording();
    expect(editor.text).toBe("c");
    expect(() => editor.playMacro(macro, 1)).toThrow();
    expect(editor.text).toBe("c");
    expect(editor.undoLabels).toEqual(['Delete "ab"']);
  });

  it("guards against misuse", () => {
    const editor = newEditor();
    expect(() => editor.stopRecording()).toThrow(/Not recording/);
    editor.startRecording("m");
    expect(() => editor.startRecording("n")).toThrow(/Already recording/);
    const macro = editor.stopRecording();
    expect(() => editor.playMacro(macro, 0)).toThrow(TypeError);
    editor.startRecording("x");
    expect(() => editor.playMacro(macro)).toThrow(/while recording/);
    expect(() => new Editor().startRecording("  ")).toThrow(TypeError);
  });

  it("does not add a history entry for a macro with no effective steps", () => {
    const editor = newEditor();
    editor.startRecording("noop");
    editor.backspace();
    const macro = editor.stopRecording();
    editor.playMacro(macro);
    expect(editor.state.canUndo).toBe(false);
  });
});

describe("Editor checkpoints, dirty state and observers", () => {
  it("restores a checkpoint as an undoable step", () => {
    const editor = newEditor("draft");
    const checkpoint = editor.checkpoint("v1");
    editor.transform("Upper", transforms.upperCase);
    typeEach(editor, "!");
    editor.restore(checkpoint);
    expect(editor.text).toBe("draft");
    expect(editor.undoLabels.at(-1)).toBe('Restore "v1"');
    editor.undo();
    expect(editor.text).toBe("DRAFT!");
  });

  it("reports dirty state and notifies listeners", () => {
    const editor = newEditor();
    const listener = vi.fn<(state: EditorState) => void>();
    const unsubscribe = editor.onChange(listener);
    editor.type("a");
    expect(listener).toHaveBeenLastCalledWith(expect.objectContaining({ text: "a", dirty: true, canUndo: true }));
    editor.markSaved();
    expect(editor.state.dirty).toBe(false);
    unsubscribe();
    editor.undo();
    expect(listener).toHaveBeenCalledTimes(2);
    expect(editor.isRecording).toBe(false);
  });
});
