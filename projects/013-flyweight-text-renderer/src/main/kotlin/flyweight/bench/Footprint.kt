package flyweight.bench

import flyweight.glyph.Glyph
import flyweight.layout.Layout
import java.util.Collections
import java.util.IdentityHashMap

/**
 * Deterministic, analytic estimate of how much heap a [Layout] retains.
 *
 * The JVM doesn't expose object sizes without an agent (JOL / Instrumentation), and
 * `Runtime` measurements are noisy, so the tests rely on this model instead. The
 * constants describe a 64-bit HotSpot JVM with compressed oops and compressed class
 * pointers (the default below 32 GB heaps): 12-byte object headers, 4-byte references,
 * 8-byte alignment. Absolute numbers are approximate; the *ratio* between shared and
 * unshared layouts is what the benchmark is about, and that is exact.
 */
object Footprint {
    private const val HEADER = 12
    private const val ARRAY_HEADER = 16
    private const val REF = 4
    private const val INT = 4

    /** Glyph: header + key ref + advance + height + coverage ref, plus its byte[]. */
    fun glyphBytes(glyph: Glyph): Long =
        align(HEADER + REF + INT + INT + REF) + align(ARRAY_HEADER + glyph.bitmapBytes)

    /** PositionedGlyph: header + glyph ref + x + y + argb. */
    val positionedGlyphBytes: Long = align(HEADER + REF + INT + INT + INT)

    fun of(layout: Layout): FootprintReport {
        val distinct = Collections.newSetFromMap(IdentityHashMap<Glyph, Boolean>())
        layout.glyphs.forEach { distinct += it.glyph }
        val listBytes = align(ARRAY_HEADER + REF * layout.glyphs.size)
        return FootprintReport(
            positionedGlyphs = layout.glyphs.size,
            distinctGlyphObjects = distinct.size,
            intrinsicBytes = distinct.sumOf(::glyphBytes),
            extrinsicBytes = positionedGlyphBytes * layout.glyphs.size + listBytes,
        )
    }

    private fun align(bytes: Int): Long = ((bytes + 7) / 8 * 8).toLong()
}

data class FootprintReport(
    val positionedGlyphs: Int,
    val distinctGlyphObjects: Int,
    /** Bytes in glyph objects and bitmaps (the part sharing eliminates). */
    val intrinsicBytes: Long,
    /** Bytes in per-occurrence position/colour records (the part every design pays). */
    val extrinsicBytes: Long,
) {
    val totalBytes: Long get() = intrinsicBytes + extrinsicBytes
}
