package flyweight.bench

import flyweight.document.TextDocument
import flyweight.document.TextStyle
import flyweight.font.FontSpec
import flyweight.font.FontStyle
import flyweight.glyph.GlyphFactory
import flyweight.glyph.GlyphProvider
import flyweight.glyph.UnsharedGlyphProvider
import flyweight.layout.LayoutEngine
import kotlin.random.Random

/** Knobs for one benchmark run. */
data class BenchmarkConfig(
    val characters: Int = 200_000,
    val fontSizePx: Int = 16,
    val lineWidthPx: Int = 800,
    val seed: Int = 42,
) {
    init {
        require(characters > 0) { "characters must be positive" }
        require(lineWidthPx > 0) { "lineWidthPx must be positive" }
    }
}

/** Outcome for one strategy (shared or unshared glyphs). */
data class StrategyResult(
    val name: String,
    val footprint: FootprintReport,
    /** Heap growth observed via `Runtime`; noisy, reported for illustration only. */
    val measuredHeapBytes: Long,
    val layoutMillis: Long,
    val rasterizations: Long,
)

data class BenchmarkResult(val config: BenchmarkConfig, val shared: StrategyResult, val unshared: StrategyResult) {
    /** How many times more memory the naive design needs, by the analytic model. */
    val savingsFactor: Double
        get() = unshared.footprint.totalBytes.toDouble() / shared.footprint.totalBytes
}

/**
 * Lays out the same synthetic document twice, once through a [GlyphFactory] and once
 * through an [UnsharedGlyphProvider], and compares the cost.
 */
class MemoryBenchmark(private val config: BenchmarkConfig) {

    fun run(): BenchmarkResult {
        val document = sampleDocument(config)
        // Unshared first so its garbage can't inflate the shared run's measurement.
        val unshared = measure("unshared", UnsharedGlyphProvider(), document)
        val shared = measure("flyweight", GlyphFactory(), document)
        return BenchmarkResult(config, shared, unshared)
    }

    private fun measure(name: String, provider: GlyphProvider, document: TextDocument): StrategyResult {
        val engine = LayoutEngine(provider, config.lineWidthPx)
        val before = usedHeapAfterGc()
        val start = System.nanoTime()
        val layout = engine.layout(document)
        val millis = (System.nanoTime() - start) / 1_000_000
        val after = usedHeapAfterGc()
        val footprint = Footprint.of(layout) // also keeps `layout` reachable until here
        return StrategyResult(name, footprint, maxOf(0, after - before), millis, provider.stats.rasterizations)
    }

    private fun usedHeapAfterGc(): Long {
        val rt = Runtime.getRuntime()
        repeat(3) {
            System.gc()
            Thread.sleep(GC_SETTLE_MILLIS)
        }
        return rt.totalMemory() - rt.freeMemory()
    }

    companion object {
        private const val GC_SETTLE_MILLIS = 20L
        private val WORDS = listOf(
            "the", "flyweight", "pattern", "shares", "intrinsic", "state", "between", "many",
            "objects", "while", "extrinsic", "state", "such", "as", "position", "and", "colour",
            "stays", "with", "the", "caller", "glyph", "cache", "editor", "render", "memory",
        )

        /**
         * Builds a realistic-looking document: English-like words, paragraph breaks, and
         * a few bold/italic/coloured spans so the cache holds more than one face.
         */
        fun sampleDocument(config: BenchmarkConfig): TextDocument {
            val random = Random(config.seed)
            val body = TextStyle(FontSpec("Serif", config.fontSizePx))
            val doc = TextDocument(body)
            val sb = StringBuilder(config.characters + 16)
            while (sb.length < config.characters) {
                sb.append(WORDS[random.nextInt(WORDS.size)])
                sb.append(if (random.nextInt(40) == 0) "\n" else " ")
            }
            sb.setLength(config.characters)
            doc.append(sb.toString(), body)

            val accents = listOf(
                body.copy(font = body.font.copy(style = FontStyle.BOLD)),
                body.copy(font = body.font.copy(style = FontStyle.ITALIC)),
                body.copy(argb = 0xFFCC2200.toInt()),
            )
            repeat(config.characters / 500) {
                val start = random.nextInt(doc.length)
                val end = minOf(doc.length, start + 5 + random.nextInt(20))
                doc.applyStyle(start, end, accents[random.nextInt(accents.size)])
            }
            return doc
        }
    }
}
