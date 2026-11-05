package flyweight.layout

import flyweight.document.TextDocument
import flyweight.document.TextStyle
import flyweight.font.FontSpec
import flyweight.glyph.GlyphFactory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class LayoutEngineTest {
    // SyntheticRasterizer: a 10px font has a 6px advance.
    private val body = TextStyle(FontSpec("Mono", 10))
    private val advance = 6

    private fun layout(text: String, maxWidth: Int, factory: GlyphFactory = GlyphFactory()): Layout {
        val doc = TextDocument(body).apply { append(text) }
        return LayoutEngine(factory, maxWidth).layout(doc)
    }

    private fun Layout.lines(): List<String> =
        glyphs.groupBy { it.y }.toSortedMap().values.map { line ->
            line.sortedBy { it.x }.joinToString("") { String(Character.toChars(it.glyph.key.codePoint)) }
        }

    @Test
    fun `places characters left to right on one line`() {
        val result = layout("abc", maxWidth = 100)
        assertEquals(listOf(0, 6, 12), result.glyphs.map { it.x })
        assertTrue(result.glyphs.all { it.y == 0 })
        assertEquals(1, result.lineCount)
        assertEquals(18, result.width)
        assertEquals(10, result.height)
    }

    @Test
    fun `repeated characters share one glyph object`() {
        val factory = GlyphFactory()
        val result = layout("aaaa", 100, factory)
        val first = result.glyphs.first().glyph
        result.glyphs.forEach { assertSame(first, it.glyph) }
        assertEquals(1, factory.stats.cachedGlyphs)
    }

    @Test
    fun `wraps at word boundaries`() {
        // Room for 5 characters per line: a trailing space still fits, the next word doesn't.
        val result = layout("one two three", maxWidth = 5 * advance)
        assertEquals(listOf("one ", "two ", "three"), result.lines())
        assertEquals(3, result.lineCount)
    }

    @Test
    fun `a space that would overflow is dropped at the break`() {
        val result = layout("ab cd", maxWidth = 2 * advance)
        assertEquals(listOf("ab", "cd"), result.lines())
    }

    @Test
    fun `breaks a word longer than the line between characters`() {
        val result = layout("abcdefgh", maxWidth = 3 * advance)
        assertEquals(listOf("abc", "def", "gh"), result.lines())
    }

    @Test
    fun `newline forces a break and blank lines take vertical space`() {
        val result = layout("a\n\nb", maxWidth = 100)
        assertEquals(3, result.lineCount)
        assertEquals(0, result.glyphs[0].y)
        assertEquals(10 + LayoutEngine.EMPTY_LINE_HEIGHT, result.glyphs[1].y)
    }

    @Test
    fun `mixed sizes on one line share a bottom baseline`() {
        val doc = TextDocument(body)
        doc.append("a")
        doc.append("B", body.copy(font = body.font.copy(sizePx = 20)))
        val result = LayoutEngine(GlyphFactory(), 200).layout(doc)
        val (small, large) = result.glyphs
        assertEquals(20, result.height)
        assertEquals(10, small.y)
        assertEquals(0, large.y)
        assertEquals(small.y + small.glyph.height, large.y + large.glyph.height)
    }

    @Test
    fun `colour is extrinsic and does not create new glyphs`() {
        val factory = GlyphFactory()
        val doc = TextDocument(body)
        doc.append("x")
        doc.append("x", body.copy(argb = 0xFF00FF00.toInt()))
        val result = LayoutEngine(factory, 200).layout(doc)
        assertSame(result.glyphs[0].glyph, result.glyphs[1].glyph)
        assertEquals(listOf(TextStyle.OPAQUE_BLACK, 0xFF00FF00.toInt()), result.glyphs.map { it.argb })
        assertEquals(1, factory.stats.cachedGlyphs)
    }

    @Test
    fun `empty document lays out to a single empty line`() {
        val result = layout("", 100)
        assertEquals(0, result.glyphs.size)
        assertEquals(1, result.lineCount)
    }

    @Test
    fun `max width must be positive`() {
        assertThrows(IllegalArgumentException::class.java) { LayoutEngine(GlyphFactory(), 0) }
    }
}
