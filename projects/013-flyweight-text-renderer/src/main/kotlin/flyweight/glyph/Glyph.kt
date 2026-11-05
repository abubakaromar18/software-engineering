package flyweight.glyph

import flyweight.font.FontSpec

/**
 * Everything that identifies one rasterized glyph: which character, in which font face.
 * This is the flyweight's *intrinsic* state and the cache key.
 */
data class GlyphKey(val codePoint: Int, val font: FontSpec) {
    init {
        require(Character.isValidCodePoint(codePoint)) { "invalid code point: $codePoint" }
    }

    override fun toString(): String = "'${String(Character.toChars(codePoint))}' @ $font"
}

/**
 * The flyweight: an immutable, rasterized glyph that can be shared by every occurrence
 * of the same character in the same font.
 *
 * It deliberately holds **no** position or colour. That *extrinsic* state belongs to
 * the caller (see [flyweight.layout.PositionedGlyph]) and is passed in at draw time.
 *
 * Identity, not structural equality, is the meaningful comparison here: the whole point
 * is that two `a`s in Serif 16px are the *same object*, so this is a plain class.
 */
class Glyph(
    val key: GlyphKey,
    /** Horizontal distance to the next glyph's origin, in pixels. */
    val advance: Int,
    /** Bitmap height in pixels (equal to the font's pixel size). */
    val height: Int,
    /** Row-major 8-bit coverage mask, `advance * height` bytes. Copied, never exposed. */
    coverage: ByteArray,
) {
    // Defensive copy: a shared flyweight must be immutable, so the caller keeps no handle on it.
    private val coverage: ByteArray = coverage.copyOf()

    init {
        require(advance > 0 && height > 0) { "glyph dimensions must be positive" }
        require(coverage.size == advance * height) { "coverage size ${coverage.size} != $advance x $height" }
    }

    /** Ink coverage in `0..255` at the given pixel, where 0 is transparent. */
    fun coverageAt(x: Int, y: Int): Int {
        require(x in 0 until advance && y in 0 until height) { "($x, $y) outside $advance x $height glyph" }
        return coverage[y * advance + x].toInt() and 0xFF
    }

    /** Size of the heavyweight part of this object: the bitmap. */
    val bitmapBytes: Int get() = coverage.size

    override fun toString(): String = "Glyph($key, ${advance}x$height)"
}
