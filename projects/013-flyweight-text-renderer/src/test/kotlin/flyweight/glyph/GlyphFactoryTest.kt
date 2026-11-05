package flyweight.glyph

import flyweight.font.FontSpec
import flyweight.font.FontStyle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertSame
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

class GlyphFactoryTest {
    private val serif = FontSpec("Serif", 16)

    @Test
    fun `same key returns the same shared instance`() {
        val factory = GlyphFactory()
        val a1 = factory.glyph(GlyphKey('a'.code, serif))
        val a2 = factory.glyph(GlyphKey('a'.code, FontSpec("Serif", 16)))
        assertSame(a1, a2)
    }

    @Test
    fun `different character, size or style produce different glyphs`() {
        val factory = GlyphFactory()
        val a = factory.glyph(GlyphKey('a'.code, serif))
        assertNotSame(a, factory.glyph(GlyphKey('b'.code, serif)))
        assertNotSame(a, factory.glyph(GlyphKey('a'.code, serif.copy(sizePx = 17))))
        assertNotSame(a, factory.glyph(GlyphKey('a'.code, serif.copy(style = FontStyle.BOLD))))
        assertEquals(4, factory.stats.cachedGlyphs)
    }

    @Test
    fun `stats count requests, rasterizations and hits`() {
        val factory = GlyphFactory()
        "banana".forEach { factory.glyph(GlyphKey(it.code, serif)) }
        val stats = factory.stats
        assertEquals(6, stats.requests)
        assertEquals(3, stats.rasterizations) // b, a, n
        assertEquals(3, stats.hits)
        assertEquals(0.5, stats.hitRate, 1e-9)
    }

    @Test
    fun `clear empties the cache so glyphs are rasterized again`() {
        val factory = GlyphFactory()
        val before = factory.glyph(GlyphKey('x'.code, serif))
        factory.clear()
        assertNotSame(before, factory.glyph(GlyphKey('x'.code, serif)))
        assertEquals(2, factory.stats.rasterizations)
    }

    @Test
    fun `unshared provider rasterizes on every request`() {
        val provider = UnsharedGlyphProvider()
        val a1 = provider.glyph(GlyphKey('a'.code, serif))
        val a2 = provider.glyph(GlyphKey('a'.code, serif))
        assertNotSame(a1, a2)
        assertEquals(2, provider.stats.rasterizations)
        assertEquals(0.0, provider.stats.hitRate, 0.0)
    }

    @Test
    fun `concurrent requests rasterize each key exactly once`() {
        val calls = AtomicInteger()
        val slowRasterizer = GlyphRasterizer { key ->
            calls.incrementAndGet()
            Thread.sleep(5)
            SyntheticRasterizer().rasterize(key)
        }
        val factory = GlyphFactory(slowRasterizer)
        val threads = 16
        val pool = Executors.newFixedThreadPool(threads)
        val start = CountDownLatch(1)
        val results = (1..threads).map {
            pool.submit<Glyph> {
                start.await()
                factory.glyph(GlyphKey('q'.code, serif))
            }
        }
        start.countDown()
        val glyphs = results.map { it.get(5, TimeUnit.SECONDS) }
        pool.shutdown()

        assertEquals(1, calls.get())
        assertTrue(glyphs.all { it === glyphs.first() })
    }

    @Test
    fun `cached bitmap bytes add up the distinct glyphs only`() {
        val factory = GlyphFactory()
        repeat(100) { factory.glyph(GlyphKey('m'.code, serif)) }
        val one = factory.glyph(GlyphKey('m'.code, serif))
        assertEquals(one.bitmapBytes.toLong(), factory.cachedBitmapBytes())
    }

    @Test
    fun `invalid code points are rejected`() {
        assertThrows(IllegalArgumentException::class.java) { GlyphKey(-1, serif) }
    }
}
