package flyweight.render

import flyweight.document.TextDocument
import flyweight.document.TextStyle
import flyweight.font.FontSpec
import flyweight.glyph.Glyph
import flyweight.glyph.GlyphFactory
import flyweight.glyph.GlyphKey
import flyweight.layout.LayoutEngine
import flyweight.layout.PositionedGlyph
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class CanvasTest {
    private val font = FontSpec("Mono", 10)
    private val red = 0xFFFF0000.toInt()

    /** 2x2 glyph: full ink top-left, half ink bottom-right. */
    private val tiny = Glyph(GlyphKey('t'.code, font), 2, 2, byteArrayOf(255.toByte(), 0, 0, 128.toByte()))

    @Test
    fun `draws glyph coverage in the extrinsic colour at the extrinsic position`() {
        val canvas = Canvas(4, 4)
        canvas.draw(PositionedGlyph(tiny, 1, 1, red))
        assertEquals(red, canvas.pixel(1, 1))
        assertEquals(Canvas.WHITE, canvas.pixel(2, 1)) // zero coverage leaves background
        assertEquals(Canvas.WHITE, canvas.pixel(0, 0))
        val half = canvas.pixel(2, 2)
        assertEquals(0xFF, (half ushr 16) and 0xFF) // red channel stays full
        assertTrue(((half ushr 8) and 0xFF) in 120..135) // green blended about halfway
    }

    @Test
    fun `the same shared glyph can be drawn in different places and colours`() {
        val canvas = Canvas(6, 2)
        canvas.draw(PositionedGlyph(tiny, 0, 0, red))
        canvas.draw(PositionedGlyph(tiny, 3, 0, TextStyle.OPAQUE_BLACK))
        assertEquals(red, canvas.pixel(0, 0))
        assertEquals(TextStyle.OPAQUE_BLACK, canvas.pixel(3, 0))
    }

    @Test
    fun `glyphs partially off-canvas are clipped, not errors`() {
        val canvas = Canvas(2, 2)
        canvas.draw(PositionedGlyph(tiny, -1, -1, red))
        canvas.draw(PositionedGlyph(tiny, 1, 1, red))
        assertEquals(red, canvas.pixel(1, 1))
    }

    @Test
    fun `blend respects source alpha`() {
        val transparent = 0x00FF0000
        assertEquals(Canvas.WHITE, Canvas.blend(Canvas.WHITE, transparent, 255))
        assertEquals(red, Canvas.blend(Canvas.WHITE, red, 255))
    }

    @Test
    fun `full pipeline renders ink and an ascii preview`() {
        val doc = TextDocument(TextStyle(FontSpec("Serif", 16))).apply { append("Hi there\nworld") }
        val layout = LayoutEngine(GlyphFactory(), 200).layout(doc)
        val canvas = Canvas.render(layout)
        val inked = (0 until canvas.height).sumOf { y -> (0 until canvas.width).count { x -> canvas.pixel(x, y) != Canvas.WHITE } }
        assertTrue(inked > 0)

        val preview = AsciiPreview.of(canvas)
        assertEquals((canvas.height + 3) / 4, preview.lines().size)
        assertNotEquals("", preview.trim())
    }

    @Test
    fun `invalid sizes are rejected`() {
        assertThrows(IllegalArgumentException::class.java) { Canvas(0, 5) }
        assertThrows(IllegalArgumentException::class.java) { AsciiPreview.of(Canvas(2, 2), cellWidth = 0) }
        assertThrows(IllegalArgumentException::class.java) { Canvas(2, 2).pixel(2, 0) }
    }
}
