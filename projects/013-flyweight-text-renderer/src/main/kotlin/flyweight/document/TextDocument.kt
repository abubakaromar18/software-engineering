package flyweight.document

import flyweight.font.FontSpec

/**
 * How a span of text looks. The font is intrinsic to the glyph (it changes the pixels);
 * the colour is extrinsic (applied at draw time), so it never multiplies the glyph cache.
 */
data class TextStyle(val font: FontSpec, val argb: Int = OPAQUE_BLACK) {
    companion object {
        const val OPAQUE_BLACK: Int = 0xFF000000.toInt()
    }
}

/** A maximal stretch of characters that share one style. */
data class StyleRun(val length: Int, val style: TextStyle) {
    init {
        require(length > 0) { "run length must be positive" }
    }
}

/**
 * Editable text with run-length-encoded styles.
 *
 * Storing a style per character would be the extrinsic-state equivalent of not sharing
 * glyphs. Instead the document keeps a list of [StyleRun]s that always sum to the text
 * length, and adjacent runs with equal styles are merged after every edit, so a
 * 100 000-character file in one font costs a single run.
 */
class TextDocument(private val defaultStyle: TextStyle) {
    private val text = StringBuilder()
    private val runs = mutableListOf<StyleRun>()

    val length: Int get() = text.length

    fun text(): String = text.toString()

    fun runs(): List<StyleRun> = runs.toList()

    /** Inserts [content] at [offset]. Uses [style] if given, otherwise the style at the caret. */
    fun insert(offset: Int, content: String, style: TextStyle? = null) {
        checkOffset(offset)
        if (content.isEmpty()) return
        val effective = style ?: caretStyle(offset)
        val index = splitAt(offset)
        runs.add(index, StyleRun(content.length, effective))
        text.insert(offset, content)
        normalize()
    }

    fun append(content: String, style: TextStyle? = null) = insert(length, content, style)

    /** Deletes the half-open range `[start, end)`. */
    fun delete(start: Int, end: Int) {
        checkRange(start, end)
        if (start == end) return
        val from = splitAt(start)
        val to = splitAt(end)
        runs.subList(from, to).clear()
        text.delete(start, end)
        normalize()
    }

    /** Restyles the half-open range `[start, end)`. */
    fun applyStyle(start: Int, end: Int, style: TextStyle) {
        checkRange(start, end)
        if (start == end) return
        val from = splitAt(start)
        val to = splitAt(end)
        runs.subList(from, to).clear()
        runs.add(from, StyleRun(end - start, style))
        normalize()
    }

    fun styleAt(offset: Int): TextStyle {
        require(offset in 0 until length) { "offset $offset outside 0 until $length" }
        var start = 0
        for (run in runs) {
            if (offset < start + run.length) return run.style
            start += run.length
        }
        error("style runs do not cover offset $offset") // unreachable while invariants hold
    }

    /** Visits each character together with its style, in order. */
    inline fun forEachStyledChar(action: (offset: Int, ch: Char, style: TextStyle) -> Unit) {
        var offset = 0
        val content = text()
        for (run in runs()) {
            repeat(run.length) {
                action(offset, content[offset], run.style)
                offset++
            }
        }
    }

    /** New text typed at the caret inherits the style of the character before it. */
    private fun caretStyle(offset: Int): TextStyle = when {
        length == 0 -> defaultStyle
        offset == 0 -> styleAt(0)
        else -> styleAt(offset - 1)
    }

    /**
     * Ensures a run boundary exists at [offset] and returns the index of the first run
     * starting at or after it.
     */
    private fun splitAt(offset: Int): Int {
        var start = 0
        for ((i, run) in runs.withIndex()) {
            if (offset == start) return i
            val end = start + run.length
            if (offset < end) {
                runs[i] = StyleRun(offset - start, run.style)
                runs.add(i + 1, StyleRun(end - offset, run.style))
                return i + 1
            }
            start = end
        }
        return runs.size
    }

    private fun normalize() {
        var i = 0
        while (i < runs.size - 1) {
            val a = runs[i]
            val b = runs[i + 1]
            if (a.style == b.style) {
                runs[i] = StyleRun(a.length + b.length, a.style)
                runs.removeAt(i + 1)
            } else {
                i++
            }
        }
        check(runs.sumOf { it.length } == text.length) { "style runs out of sync with text" }
    }

    private fun checkOffset(offset: Int) =
        require(offset in 0..length) { "offset $offset outside 0..$length" }

    private fun checkRange(start: Int, end: Int) =
        require(start in 0..end && end <= length) { "range [$start, $end) outside 0..$length" }
}
