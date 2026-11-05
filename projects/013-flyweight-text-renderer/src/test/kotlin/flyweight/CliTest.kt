package flyweight

import flyweight.bench.BenchmarkConfig
import flyweight.bench.MemoryBenchmark
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class CliTest {
    @Test
    fun `parses named options and positional words`() {
        val options = CliOptions.parse(listOf("--width", "120", "hello", "world"))
        assertEquals(120, options.int("width", 0))
        assertEquals(7, options.int("size", 7))
        assertEquals(listOf("hello", "world"), options.positional)
    }

    @Test
    fun `reports bad option values as usage errors`() {
        assertThrows(UsageException::class.java) { CliOptions.parse(listOf("--width")) }
        val options = CliOptions.parse(listOf("--width", "wide"))
        assertThrows(UsageException::class.java) { options.int("width", 0) }
    }

    @Test
    fun `report lists both strategies and the savings`() {
        val report = formatReport(MemoryBenchmark(BenchmarkConfig(characters = 2_000)).run())
        assertTrue(report.contains("unshared"))
        assertTrue(report.contains("flyweight"))
        assertTrue(report.contains("less memory"))
    }
}
