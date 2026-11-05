package flyweight.font

/** Weight/slant combination of a font face. */
enum class FontStyle { REGULAR, BOLD, ITALIC, BOLD_ITALIC;

    val isBold: Boolean get() = this == BOLD || this == BOLD_ITALIC
    val isItalic: Boolean get() = this == ITALIC || this == BOLD_ITALIC
}

/**
 * Identifies a concrete font face at a concrete pixel size.
 *
 * A `FontSpec` is a value object: two specs with the same family, size and style are
 * interchangeable, which is exactly what lets the glyph cache use it as part of its key.
 */
data class FontSpec(val family: String, val sizePx: Int, val style: FontStyle = FontStyle.REGULAR) {
    init {
        require(family.isNotBlank()) { "font family must not be blank" }
        require(sizePx in MIN_SIZE_PX..MAX_SIZE_PX) { "font size must be in $MIN_SIZE_PX..$MAX_SIZE_PX px, was $sizePx" }
    }

    override fun toString(): String = "$family ${sizePx}px ${style.name.lowercase()}"

    companion object {
        const val MIN_SIZE_PX = 4
        const val MAX_SIZE_PX = 256
    }
}
