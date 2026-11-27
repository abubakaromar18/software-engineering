"""Probabilistic data structures with tunable, measurable error rates.

Public API:

* :class:`BloomFilter` - set membership with no false negatives and a
  configurable false-positive rate.
* :class:`ScalableBloomFilter` - a Bloom filter that grows on demand while
  keeping a bound on the compound false-positive rate.
* :class:`CountMinSketch` - frequency estimation that never under-counts and
  over-counts by at most ``epsilon * N`` with probability ``1 - delta``.
* :class:`TopK` - heavy-hitter tracking on top of a Count-Min sketch.
"""

from sketches.bloom import BloomFilter, BloomParameters, ScalableBloomFilter
from sketches.count_min import CountMinSketch, TopK

__all__ = [
    "BloomFilter",
    "BloomParameters",
    "CountMinSketch",
    "ScalableBloomFilter",
    "TopK",
]

__version__ = "1.0.0"
