package flyweight.bench

import flyweight.document.TextDocument
import flyweight.document.TextStyle
import flyweight.font.FontSpec
import flyweight.glyph.GlyphFactory
import flyweight.glyph.UnsharedGlyphProvider
import flyweight.layout.LayoutEngine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class BenchmarkTest {
    private val body = TextStyle(FontSpec("Serif", 16))

    private fun doc(text: String) = TextDocument(body).apply { append(text) }

    @Test
    fun `footprint counts distinct glyph objects by identity`() {
        val text = "abababab"
        val shared = Footprint.of(LayoutEngine(GlyphFactory(), 1000).layout(doc(text)))
        val unshared = Footprint.of(LayoutEngine(UnsharedGlyphProvider(), 1000).layout(doc(text)))

        assertEquals(8, shared.positionedGlyphs)
        assertEquals(2, shared.distinctGlyphObjects)
        assertEquals(8, unshared.distinctGlyphObjects)
        // Extrinsic state is the same in both designs; only intrinsic cost changes.
        assertEquals(shared.extrinsicBytes, unshared.extrinsicBytes)
        assertEquals(shared.intrinsicBytes * 4, unshared.intrinsicBytes)
    }

    @Test
    fun `glyph footprint includes object and bitmap with 8-byte alignment`() {
        val glyph = GlyphFactory().glyph(flyweight.glyph.GlyphKey('a'.code, body.font))
        val bytes = Footprint.glyphBytes(glyph)
        assertEquals(0L, bytes % 8)
        assertTrue(bytes >= glyph.bitmapBytes + 16)
    }

    @Test
    fun `sample document is deterministic for a seed and has the requested length`() {
        val config = BenchmarkConfig(characters = 5_000, seed = 7)
        val a = MemoryBenchmark.sampleDocument(config)
        val b = MemoryBenchmark.sampleDocument(config)
        assertEquals(5_000, a.length)
        assertEquals(a.text(), b.text())
        assertEquals(a.runs(), b.runs())
        assertTrue("accent styles should be applied", a.runs().size > 1)
    }

    @Test
    fun `flyweight run is dramatically smaller than the unshared run`() {
        val result = MemoryBenchmark(BenchmarkConfig(characters = 20_000)).run()

        assertEquals(result.shared.footprint.positionedGlyphs, result.unshared.footprint.positionedGlyphs)
        assertTrue(result.shared.footprint.distinctGlyphObjects < 150)
        assertEquals(result.shared.footprint.distinctGlyphObjects.toLong(), result.shared.rasterizations)
        // Unshared rasterizes per request; spaces dropped at line breaks were requested too.
        assertTrue(result.unshared.rasterizations >= result.unshared.footprint.positionedGlyphs)
        assertTrue("expected >5x savings, got ${result.savingsFactor}", result.savingsFactor > 5.0)
    }

    @Test
    fun `invalid config is rejected`() {
        assertThrows(IllegalArgumentException::class.java) { BenchmarkConfig(characters = 0) }
        assertThrows(IllegalArgumentException::class.java) { BenchmarkConfig(lineWidthPx = -1) }
    }
}
