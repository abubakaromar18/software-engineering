package flyweight.glyph

import flyweight.font.FontSpec
import flyweight.font.FontStyle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class GlyphAndRasterizerTest {
    private val rasterizer = SyntheticRasterizer()
    private val serif = FontSpec("Serif", 20)

    private fun Glyph.inkPixels(): Int =
        (0 until height).sumOf { y -> (0 until advance).count { x -> coverageAt(x, y) > 0 } }

    @Test
    fun `font spec validates its fields`() {
        assertThrows(IllegalArgumentException::class.java) { FontSpec(" ", 12) }
        assertThrows(IllegalArgumentException::class.java) { FontSpec("Serif", 2) }
        assertThrows(IllegalArgumentException::class.java) { FontSpec("Serif", 1000) }
        assertEquals(FontSpec("Mono", 12, FontStyle.BOLD), FontSpec("Mono", 12, FontStyle.BOLD))
    }

    @Test
    fun `rasterization is deterministic`() {
        val key = GlyphKey('g'.code, serif)
        val a = rasterizer.rasterize(key)
        val b = rasterizer.rasterize(key)
        for (y in 0 until a.height) for (x in 0 until a.advance) {
            assertEquals(a.coverageAt(x, y), b.coverageAt(x, y))
        }
    }

    @Test
    fun `glyph size scales with font size and bold is wider`() {
        val small = rasterizer.rasterize(GlyphKey('a'.code, FontSpec("Serif", 10)))
        val large = rasterizer.rasterize(GlyphKey('a'.code, FontSpec("Serif", 40)))
        val bold = rasterizer.rasterize(GlyphKey('a'.code, FontSpec("Serif", 10, FontStyle.BOLD)))
        assertEquals(10, small.height)
        assertEquals(40, large.height)
        assertTrue(large.bitmapBytes > small.bitmapBytes * 10)
        assertEquals(small.advance + 1, bold.advance)
    }

    @Test
    fun `whitespace has no ink and letters do`() {
        assertEquals(0, rasterizer.rasterize(GlyphKey(' '.code, serif)).inkPixels())
        assertTrue(rasterizer.rasterize(GlyphKey('A'.code, serif)).inkPixels() > 0)
    }

    @Test
    fun `glyph copies its bitmap so later mutation cannot leak into a shared flyweight`() {
        val bytes = ByteArray(4) { 10 }
        val glyph = Glyph(GlyphKey('x'.code, serif), advance = 2, height = 2, coverage = bytes)
        bytes[0] = 99
        assertEquals(10, glyph.coverageAt(0, 0))
    }

    @Test
    fun `glyph rejects inconsistent dimensions and out-of-range reads`() {
        val key = GlyphKey('x'.code, serif)
        assertThrows(IllegalArgumentException::class.java) { Glyph(key, 2, 2, ByteArray(3)) }
        val glyph = Glyph(key, 2, 2, ByteArray(4))
        assertThrows(IllegalArgumentException::class.java) { glyph.coverageAt(2, 0) }
        assertFalse(glyph.toString().isBlank())
    }
}
