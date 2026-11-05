package flyweight.glyph

import flyweight.font.FontSpec

/**
 * Turns a [GlyphKey] into pixels. In a real editor this would call FreeType, DirectWrite
 * or CoreText and is comparatively slow, which is the second reason (after memory) to
 * cache its output.
 */
fun interface GlyphRasterizer {
    fun rasterize(key: GlyphKey): Glyph
}

/**
 * A deterministic stand-in for a real font engine, so the project needs no font files.
 *
 * It produces a monospaced bitmap whose ink pattern is derived from the code point:
 * a border-ish "letter body" plus pseudo-random interior pixels. The shapes are not
 * readable letters, but they have the properties that matter for this exercise:
 * real per-glyph memory cost that scales with font size, distinct output per key,
 * and whitespace that renders as empty.
 */
class SyntheticRasterizer : GlyphRasterizer {

    override fun rasterize(key: GlyphKey): Glyph {
        val font = key.font
        val width = advanceFor(font)
        val height = font.sizePx
        val pixels = ByteArray(width * height)
        if (!Character.isWhitespace(key.codePoint)) paintBody(key, width, height, pixels)
        return Glyph(key, width, height, pixels)
    }

    /** Roughly 0.6em wide, one pixel wider for bold faces. */
    private fun advanceFor(font: FontSpec): Int =
        maxOf(2, (font.sizePx * 3 + 4) / 5) + if (font.style.isBold) 1 else 0

    private fun paintBody(key: GlyphKey, width: Int, height: Int, pixels: ByteArray) {
        // Leave a one-pixel side bearing and a descender/ascender gap so glyphs don't touch.
        val top = height / 5
        val bottom = height - maxOf(1, height / 8)
        val left = 1
        val right = width - 1
        val slant = key.font.style.isItalic
        val seed = key.codePoint * 0x9E3779B1.toInt()

        for (y in top until bottom) {
            // Italic faces shift upper rows right by up to two pixels.
            val shift = if (slant) ((bottom - y) * 2) / (bottom - top) else 0
            for (x in left until right) {
                val sx = x - shift
                if (sx < left) continue
                val onEdge = sx == left || y == top || y == bottom - 1
                val hash = mix(seed, sx, y)
                val ink = when {
                    onEdge && (hash and 3) != 0 -> 255
                    (hash and 7) == 0 -> 160
                    else -> 0
                }
                if (ink > 0) pixels[y * width + x] = ink.toByte()
            }
        }
    }

    private fun mix(seed: Int, x: Int, y: Int): Int {
        var h = seed xor (x * 73856093) xor (y * 19349663)
        h = h xor (h ushr 13)
        h *= 0x5bd1e995
        return h xor (h ushr 15)
    }
}
