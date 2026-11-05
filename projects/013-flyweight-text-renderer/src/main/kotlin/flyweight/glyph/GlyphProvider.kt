package flyweight.glyph

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong

/**
 * Where the layout engine gets glyphs from. Two implementations exist so the benchmark
 * can swap them without touching any other code: [GlyphFactory] (shared flyweights)
 * and [UnsharedGlyphProvider] (a fresh object per request, the naive baseline).
 */
interface GlyphProvider {
    fun glyph(key: GlyphKey): Glyph
    val stats: GlyphStats
}

/** Snapshot of how a provider has been used. */
data class GlyphStats(val requests: Long, val rasterizations: Long, val cachedGlyphs: Int) {
    val hits: Long get() = requests - rasterizations
    val hitRate: Double get() = if (requests == 0L) 0.0 else hits.toDouble() / requests
}

/**
 * The Flyweight Factory: hands out one shared [Glyph] per [GlyphKey].
 *
 * Thread-safe. `ConcurrentHashMap.computeIfAbsent` guarantees the rasterizer runs at
 * most once per key even when several threads lay out text concurrently.
 *
 * The cache is unbounded on purpose: the key space an editor actually touches is small
 * (a few hundred code points times a handful of faces). A bounded LRU is listed as an
 * extension in the README.
 */
class GlyphFactory(private val rasterizer: GlyphRasterizer = SyntheticRasterizer()) : GlyphProvider {
    private val cache = ConcurrentHashMap<GlyphKey, Glyph>()
    private val requests = AtomicLong()
    private val rasterizations = AtomicLong()

    override fun glyph(key: GlyphKey): Glyph {
        requests.incrementAndGet()
        return cache.computeIfAbsent(key) {
            rasterizations.incrementAndGet()
            rasterizer.rasterize(it)
        }
    }

    override val stats: GlyphStats
        get() = GlyphStats(requests.get(), rasterizations.get(), cache.size)

    /** Total bitmap bytes held by the cache. */
    fun cachedBitmapBytes(): Long = cache.values.sumOf { it.bitmapBytes.toLong() }

    /** Drops every cached glyph, e.g. after a DPI change invalidates all bitmaps. */
    fun clear() = cache.clear()
}

/**
 * Baseline without sharing: every request rasterizes a brand-new glyph. Functionally
 * identical output, very different memory profile.
 */
class UnsharedGlyphProvider(private val rasterizer: GlyphRasterizer = SyntheticRasterizer()) : GlyphProvider {
    private val requests = AtomicLong()

    override fun glyph(key: GlyphKey): Glyph {
        requests.incrementAndGet()
        return rasterizer.rasterize(key)
    }

    override val stats: GlyphStats
        get() = requests.get().let { GlyphStats(it, it, 0) }
}
