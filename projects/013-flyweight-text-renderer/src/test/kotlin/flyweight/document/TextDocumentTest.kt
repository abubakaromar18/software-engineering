package flyweight.document

import flyweight.font.FontSpec
import flyweight.font.FontStyle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class TextDocumentTest {
    private val body = TextStyle(FontSpec("Serif", 16))
    private val bold = body.copy(font = body.font.copy(style = FontStyle.BOLD))
    private val red = body.copy(argb = 0xFFFF0000.toInt())

    @Test
    fun `appending in one style keeps a single run`() {
        val doc = TextDocument(body)
        doc.append("hello ")
        doc.append("world")
        assertEquals("hello world", doc.text())
        assertEquals(listOf(StyleRun(11, body)), doc.runs())
    }

    @Test
    fun `typed text inherits the style before the caret`() {
        val doc = TextDocument(body)
        doc.append("ab", bold)
        doc.insert(2, "c")
        assertEquals(listOf(StyleRun(3, bold)), doc.runs())
    }

    @Test
    fun `applying a style splits runs and restyling back merges them`() {
        val doc = TextDocument(body)
        doc.append("hello world")
        doc.applyStyle(6, 11, bold)
        assertEquals(listOf(StyleRun(6, body), StyleRun(5, bold)), doc.runs())
        doc.applyStyle(2, 4, red)
        assertEquals(
            listOf(StyleRun(2, body), StyleRun(2, red), StyleRun(2, body), StyleRun(5, bold)),
            doc.runs(),
        )
        doc.applyStyle(0, 11, body)
        assertEquals(listOf(StyleRun(11, body)), doc.runs())
    }

    @Test
    fun `inserting styled text in the middle of a run`() {
        val doc = TextDocument(body)
        doc.append("helloworld")
        doc.insert(5, " big ", bold)
        assertEquals("hello big world", doc.text())
        assertEquals(listOf(StyleRun(5, body), StyleRun(5, bold), StyleRun(5, body)), doc.runs())
        assertEquals(bold, doc.styleAt(7))
    }

    @Test
    fun `deleting across runs removes them and merges neighbours`() {
        val doc = TextDocument(body)
        doc.append("aaa")
        doc.append("BBB", bold)
        doc.append("aaa", body)
        doc.delete(2, 7)
        assertEquals("aaaa", doc.text())
        assertEquals(listOf(StyleRun(4, body)), doc.runs())
    }

    @Test
    fun `deleting everything leaves an empty document`() {
        val doc = TextDocument(body)
        doc.append("abc", red)
        doc.delete(0, 3)
        assertEquals(0, doc.length)
        assertEquals(emptyList<StyleRun>(), doc.runs())
        doc.insert(0, "x")
        assertEquals(listOf(StyleRun(1, body)), doc.runs()) // falls back to the default style
    }

    @Test
    fun `forEachStyledChar visits every character with its style`() {
        val doc = TextDocument(body)
        doc.append("ab")
        doc.append("c", bold)
        val seen = mutableListOf<Triple<Int, Char, TextStyle>>()
        doc.forEachStyledChar { i, ch, style -> seen += Triple(i, ch, style) }
        assertEquals(listOf(Triple(0, 'a', body), Triple(1, 'b', body), Triple(2, 'c', bold)), seen)
    }

    @Test
    fun `out of range edits are rejected`() {
        val doc = TextDocument(body)
        doc.append("abc")
        assertThrows(IllegalArgumentException::class.java) { doc.insert(4, "x") }
        assertThrows(IllegalArgumentException::class.java) { doc.delete(2, 1) }
        assertThrows(IllegalArgumentException::class.java) { doc.applyStyle(0, 9, bold) }
        assertThrows(IllegalArgumentException::class.java) { doc.styleAt(3) }
    }
}
