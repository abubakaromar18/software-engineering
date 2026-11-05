package flyweight.layout

import flyweight.document.TextDocument
import flyweight.glyph.Glyph
import flyweight.glyph.GlyphKey
import flyweight.glyph.GlyphProvider

/**
 * A flyweight in context: the shared [glyph] plus the extrinsic state that differs per
 * occurrence (where it sits and what colour it is drawn in). This is the small object
 * that exists once per character; the heavy bitmap behind it exists once per key.
 */
data class PositionedGlyph(val glyph: Glyph, val x: Int, val y: Int, val argb: Int)

/** Result of laying out a document. */
data class Layout(val glyphs: List<PositionedGlyph>, val width: Int, val height: Int, val lineCount: Int)

/**
 * Greedy word-wrapping layout.
 *
 * - `\n` forces a line break.
 * - A word that would overflow [maxWidth] moves to the next line; a single word wider
 *   than [maxWidth] is broken between characters.
 * - Spaces that land at a wrap point are dropped, like every word processor does.
 * - Each line is as tall as its tallest glyph, so mixed font sizes stack correctly.
 *
 * Text is treated as UTF-16 code units, which covers the Basic Multilingual Plane.
 */
class LayoutEngine(private val glyphs: GlyphProvider, private val maxWidth: Int) {
    init {
        require(maxWidth > 0) { "maxWidth must be positive" }
    }

    fun layout(document: TextDocument): Layout {
        val lines = mutableListOf<MutableList<Cell>>(mutableListOf())
        val word = mutableListOf<Cell>()
        var lineWidth = 0

        fun newLine() {
            lines += mutableListOf<Cell>()
            lineWidth = 0
        }

        fun place(cell: Cell) {
            lines.last() += cell
            lineWidth += cell.glyph.advance
        }

        fun flushWord() {
            val wordWidth = word.sumOf { it.glyph.advance }
            if (lineWidth > 0 && lineWidth + wordWidth > maxWidth) newLine()
            for (cell in word) {
                // Only a word longer than a whole line gets here with an overflow: hard-break it.
                if (lineWidth > 0 && lineWidth + cell.glyph.advance > maxWidth) newLine()
                place(cell)
            }
            word.clear()
        }

        document.forEachStyledChar { _, ch, style ->
            when {
                ch == '\n' -> {
                    flushWord()
                    newLine()
                }
                ch == ' ' || ch == '\t' -> {
                    flushWord()
                    val cell = Cell(glyphs.glyph(GlyphKey(' '.code, style.font)), style.argb)
                    if (lineWidth + cell.glyph.advance > maxWidth) newLine() else place(cell)
                }
                else -> word += Cell(glyphs.glyph(GlyphKey(ch.code, style.font)), style.argb)
            }
        }
        flushWord()

        return assemble(lines)
    }

    /** Second pass: now that each line's height is known, assign absolute coordinates. */
    private fun assemble(lines: List<List<Cell>>): Layout {
        val placed = ArrayList<PositionedGlyph>(lines.sumOf { it.size })
        var y = 0
        var width = 0
        for (line in lines) {
            val lineHeight = line.maxOfOrNull { it.glyph.height } ?: EMPTY_LINE_HEIGHT
            var x = 0
            for (cell in line) {
                // Bottom-align glyphs of different sizes on a shared baseline.
                placed += PositionedGlyph(cell.glyph, x, y + lineHeight - cell.glyph.height, cell.argb)
                x += cell.glyph.advance
            }
            width = maxOf(width, x)
            y += lineHeight
        }
        return Layout(placed, width, y, lines.size)
    }

    private data class Cell(val glyph: Glyph, val argb: Int)

    companion object {
        /** Height given to blank lines, which have no glyph to measure. */
        const val EMPTY_LINE_HEIGHT = 16
    }
}
