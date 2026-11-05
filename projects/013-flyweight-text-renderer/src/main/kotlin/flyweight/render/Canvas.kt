package flyweight.render

import flyweight.layout.Layout
import flyweight.layout.PositionedGlyph

/**
 * An ARGB raster that glyphs are composited onto.
 *
 * Drawing is where intrinsic and extrinsic state finally meet: the shared glyph supplies
 * coverage, the [PositionedGlyph] supplies position and colour.
 */
class Canvas(val width: Int, val height: Int, background: Int = WHITE) {
    init {
        require(width > 0 && height > 0) { "canvas must be at least 1x1, was ${width}x$height" }
    }

    private val pixels = IntArray(width * height) { background }

    fun pixel(x: Int, y: Int): Int {
        require(x in 0 until width && y in 0 until height) { "($x, $y) outside canvas" }
        return pixels[y * width + x]
    }

    fun draw(placed: PositionedGlyph) {
        val glyph = placed.glyph
        for (gy in 0 until glyph.height) {
            val cy = placed.y + gy
            if (cy !in 0 until height) continue
            for (gx in 0 until glyph.advance) {
                val cx = placed.x + gx
                if (cx !in 0 until width) continue
                val coverage = glyph.coverageAt(gx, gy)
                if (coverage == 0) continue
                val i = cy * width + cx
                pixels[i] = blend(pixels[i], placed.argb, coverage)
            }
        }
    }

    fun drawAll(layout: Layout) = layout.glyphs.forEach(::draw)

    companion object {
        const val WHITE: Int = 0xFFFFFFFF.toInt()

        /** Renders a whole layout onto a canvas sized to fit it. */
        fun render(layout: Layout): Canvas =
            Canvas(maxOf(1, layout.width), maxOf(1, layout.height)).also { it.drawAll(layout) }

        /** Source-over blend of [color] onto [dst], scaled by glyph [coverage] (0..255). */
        internal fun blend(dst: Int, color: Int, coverage: Int): Int {
            val alpha = ((color ushr 24) and 0xFF) * coverage / 255
            fun channel(shift: Int): Int {
                val d = (dst ushr shift) and 0xFF
                val s = (color ushr shift) and 0xFF
                return (s * alpha + d * (255 - alpha)) / 255
            }
            return (0xFF shl 24) or (channel(16) shl 16) or (channel(8) shl 8) or channel(0)
        }
    }
}

/** Downsamples a canvas to characters so a render can be eyeballed in a terminal. */
object AsciiPreview {
    private const val RAMP = " .:-=+*#%@"

    fun of(canvas: Canvas, cellWidth: Int = 2, cellHeight: Int = 4): String {
        require(cellWidth > 0 && cellHeight > 0) { "cell size must be positive" }
        val out = StringBuilder()
        for (top in 0 until canvas.height step cellHeight) {
            for (left in 0 until canvas.width step cellWidth) {
                out.append(RAMP[darkness(canvas, left, top, cellWidth, cellHeight) * (RAMP.length - 1) / 255])
            }
            out.append('\n')
        }
        return out.toString().lines().joinToString("\n") { it.trimEnd() }.trimEnd('\n')
    }

    /** Average darkness (0 = white, 255 = black) of one block of pixels. */
    private fun darkness(canvas: Canvas, left: Int, top: Int, w: Int, h: Int): Int {
        var total = 0
        var count = 0
        for (y in top until minOf(top + h, canvas.height)) {
            for (x in left until minOf(left + w, canvas.width)) {
                val p = canvas.pixel(x, y)
                val luma = (((p ushr 16) and 0xFF) * 299 + ((p ushr 8) and 0xFF) * 587 + (p and 0xFF) * 114) / 1000
                total += 255 - luma
                count++
            }
        }
        return total / count
    }
}
