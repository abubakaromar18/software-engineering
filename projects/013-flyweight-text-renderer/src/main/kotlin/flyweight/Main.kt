package flyweight

import flyweight.bench.BenchmarkConfig
import flyweight.bench.BenchmarkResult
import flyweight.bench.MemoryBenchmark
import flyweight.document.TextDocument
import flyweight.document.TextStyle
import flyweight.font.FontSpec
import flyweight.font.FontStyle
import flyweight.glyph.GlyphFactory
import flyweight.layout.LayoutEngine
import flyweight.render.AsciiPreview
import flyweight.render.Canvas
import kotlin.system.exitProcess

private const val USAGE = """usage:
  flyweight render [--width PX] [--size PX] <text>   lay out and preview text as ASCII art
  flyweight bench  [--chars N] [--size PX] [--width PX]   compare memory with/without sharing"""

fun main(args: Array<String>) {
    try {
        val command = args.firstOrNull() ?: throw UsageException("missing command")
        val options = CliOptions.parse(args.drop(1))
        when (command) {
            "render" -> render(options)
            "bench" -> bench(options)
            "help", "--help", "-h" -> println(USAGE)
            else -> throw UsageException("unknown command '$command'")
        }
    } catch (e: UsageException) {
        System.err.println("error: ${e.message}\n$USAGE")
        exitProcess(2)
    } catch (e: IllegalArgumentException) {
        System.err.println("error: ${e.message}")
        exitProcess(1)
    }
}

private fun render(options: CliOptions) {
    val text = options.positional.joinToString(" ").ifBlank { throw UsageException("render needs some text") }
    val size = options.int("size", 16)
    val body = TextStyle(FontSpec("Serif", size))
    val document = TextDocument(body).apply { append(text) }
    // Bold the first word to show that a second face gets its own cache entries.
    val firstSpace = text.indexOf(' ').takeIf { it > 0 } ?: text.length
    document.applyStyle(0, firstSpace, body.copy(font = body.font.copy(style = FontStyle.BOLD)))

    val factory = GlyphFactory()
    val layout = LayoutEngine(factory, options.int("width", 320)).layout(document)
    println(AsciiPreview.of(Canvas.render(layout)))
    val stats = factory.stats
    println()
    println("${layout.glyphs.size} glyphs on ${layout.lineCount} line(s), ${layout.width}x${layout.height}px")
    println("glyph cache: ${stats.cachedGlyphs} entries, ${stats.requests} requests, " +
        "hit rate ${"%.1f".format(stats.hitRate * 100)}%")
}

private fun bench(options: CliOptions) {
    val config = BenchmarkConfig(
        characters = options.int("chars", 200_000),
        fontSizePx = options.int("size", 16),
        lineWidthPx = options.int("width", 800),
    )
    println(formatReport(MemoryBenchmark(config).run()))
}

internal fun formatReport(result: BenchmarkResult): String = buildString {
    val c = result.config
    appendLine("Flyweight benchmark: ${c.characters} chars, ${c.fontSizePx}px, ${c.lineWidthPx}px lines")
    appendLine()
    appendLine("%-10s %10s %10s %14s %14s %14s %8s".format(
        "strategy", "glyph objs", "rasterized", "intrinsic", "extrinsic", "measured heap", "layout"))
    for (r in listOf(result.unshared, result.shared)) {
        appendLine("%-10s %10d %10d %14s %14s %14s %6dms".format(
            r.name, r.footprint.distinctGlyphObjects, r.rasterizations,
            mib(r.footprint.intrinsicBytes), mib(r.footprint.extrinsicBytes), mib(r.measuredHeapBytes), r.layoutMillis))
    }
    appendLine()
    append("Sharing glyphs uses %.1fx less memory (analytic model; measured heap is GC-noisy).".format(result.savingsFactor))
}

private fun mib(bytes: Long): String = "%.2f MiB".format(bytes / (1024.0 * 1024.0))

internal class UsageException(message: String) : RuntimeException(message)

/** Minimal `--key value` parser; anything else is positional. */
internal class CliOptions private constructor(
    private val named: Map<String, String>,
    val positional: List<String>,
) {
    fun int(name: String, default: Int): Int {
        val raw = named[name] ?: return default
        return raw.toIntOrNull() ?: throw UsageException("--$name expects an integer, got '$raw'")
    }

    companion object {
        fun parse(args: List<String>): CliOptions {
            val named = mutableMapOf<String, String>()
            val positional = mutableListOf<String>()
            var i = 0
            while (i < args.size) {
                val arg = args[i]
                if (arg.startsWith("--")) {
                    val value = args.getOrNull(i + 1) ?: throw UsageException("$arg needs a value")
                    named[arg.removePrefix("--")] = value
                    i += 2
                } else {
                    positional += arg
                    i++
                }
            }
            return CliOptions(named, positional)
        }
    }
}
