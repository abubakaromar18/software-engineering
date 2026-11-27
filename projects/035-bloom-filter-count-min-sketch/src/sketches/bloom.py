"""Bloom filters: approximate set membership with one-sided error.

A Bloom filter answers "have I seen x?" with either *definitely not* or
*probably yes*. It never forgets an inserted item (no false negatives), and the
probability of a false "yes" is tuned by the two parameters:

* ``m`` - number of bits
* ``k`` - number of hash functions

For ``n`` inserted items the false-positive rate is approximately
``(1 - e^(-k n / m))^k``, minimised at ``k = (m / n) ln 2``. Solving for ``m``
gives the sizing formula used by :func:`optimal_parameters`:

    m = -n ln(p) / (ln 2)^2
"""

from __future__ import annotations

import math
import struct
from collections.abc import Iterable
from dataclasses import dataclass

from sketches.bitarray import BitArray
from sketches.hashing import Hashable, indexes

_LN2_SQUARED = math.log(2) ** 2


@dataclass(frozen=True)
class BloomParameters:
    """Sizing for a Bloom filter that holds ``capacity`` items at ``error_rate``."""

    num_bits: int
    num_hashes: int
    capacity: int
    error_rate: float

    @property
    def bits_per_item(self) -> float:
        return self.num_bits / self.capacity


def optimal_parameters(capacity: int, error_rate: float) -> BloomParameters:
    """Return the smallest ``(m, k)`` that meets ``error_rate`` at ``capacity`` items."""
    if capacity < 1:
        raise ValueError("capacity must be at least 1")
    if not 0.0 < error_rate < 1.0:
        raise ValueError("error_rate must be strictly between 0 and 1")
    num_bits = math.ceil(-capacity * math.log(error_rate) / _LN2_SQUARED)
    num_hashes = max(1, round(num_bits / capacity * math.log(2)))
    return BloomParameters(num_bits, num_hashes, capacity, error_rate)


def theoretical_fpr(num_bits: int, num_hashes: int, items: int) -> float:
    """Expected false-positive rate after inserting ``items`` distinct items."""
    if items <= 0:
        return 0.0
    return (1.0 - math.exp(-num_hashes * items / num_bits)) ** num_hashes


class BloomFilter:
    """A classic (non-counting) Bloom filter.

    Supports ``str``, ``bytes`` and ``int`` items. Two filters with the same
    ``num_bits``, ``num_hashes`` and ``seed`` can be combined with ``|`` and
    ``&`` and round-trip through :meth:`to_bytes` / :meth:`from_bytes`.
    """

    # Serialisation header: magic, version, num_bits, num_hashes, seed, items_added.
    _HEADER = struct.Struct(">4sBQIQQ")
    _MAGIC = b"BLMF"
    _VERSION = 1

    def __init__(self, num_bits: int, num_hashes: int, *, seed: int = 0) -> None:
        if num_bits < 1:
            raise ValueError("num_bits must be at least 1")
        if num_hashes < 1:
            raise ValueError("num_hashes must be at least 1")
        self._bits = BitArray(num_bits)
        self._num_hashes = num_hashes
        self._seed = seed
        self._items_added = 0

    @classmethod
    def from_capacity(cls, capacity: int, error_rate: float, *, seed: int = 0) -> BloomFilter:
        """Build a filter sized for ``capacity`` items at ``error_rate``."""
        params = optimal_parameters(capacity, error_rate)
        return cls(params.num_bits, params.num_hashes, seed=seed)

    # -- core operations -------------------------------------------------

    def add(self, item: Hashable) -> bool:
        """Insert ``item``; return ``True`` if it was definitely not present before.

        A ``False`` return means every probed bit was already set, i.e. the item
        was present *or* is a false positive. ``items_added`` only counts calls
        that changed the filter, which makes it a better estimate of distinct
        insertions than a raw call counter.
        """
        changed = False
        for index in indexes(item, self._num_hashes, len(self._bits), self._seed):
            if not self._bits.set(index):
                changed = True
        if changed:
            self._items_added += 1
        return changed

    def update(self, items: Iterable[Hashable]) -> None:
        for item in items:
            self.add(item)

    def __contains__(self, item: Hashable) -> bool:
        return all(
            self._bits[index]
            for index in indexes(item, self._num_hashes, len(self._bits), self._seed)
        )

    # -- introspection ----------------------------------------------------

    @property
    def num_bits(self) -> int:
        return len(self._bits)

    @property
    def num_hashes(self) -> int:
        return self._num_hashes

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def items_added(self) -> int:
        return self._items_added

    @property
    def fill_ratio(self) -> float:
        """Fraction of bits set; 0.5 is the optimum for a fully loaded filter."""
        return self._bits.count() / self.num_bits

    def estimated_fpr(self) -> float:
        """False-positive rate implied by the *actual* fill ratio.

        A random absent item is reported present only if all ``k`` probes hit
        set bits, so the rate is ``fill_ratio ** k``. Unlike
        :func:`theoretical_fpr`, this stays correct after unions or when the
        insert count is unknown.
        """
        return self.fill_ratio**self._num_hashes

    def estimated_cardinality(self) -> float:
        """Estimate distinct items inserted from the bit count (Swamidass & Baldi).

        ``n* = -(m / k) ln(1 - X / m)`` where ``X`` is the number of set bits.
        Returns ``inf`` for a saturated filter, where the estimate diverges.
        """
        set_bits = self._bits.count()
        if set_bits == self.num_bits:
            return math.inf
        return -self.num_bits / self._num_hashes * math.log(1.0 - set_bits / self.num_bits)

    # -- set algebra ------------------------------------------------------

    def _check_compatible(self, other: BloomFilter) -> None:
        if not isinstance(other, BloomFilter):
            raise TypeError("operand must be a BloomFilter")
        if (self.num_bits, self._num_hashes, self._seed) != (
            other.num_bits,
            other._num_hashes,
            other._seed,
        ):
            raise ValueError("filters must share num_bits, num_hashes and seed")

    def _with_bits(self, bits: BitArray, items_added: int) -> BloomFilter:
        result = BloomFilter(self.num_bits, self._num_hashes, seed=self._seed)
        result._bits = bits
        result._items_added = items_added
        return result

    def __or__(self, other: BloomFilter) -> BloomFilter:
        """Union: exactly the filter you'd get by inserting both item sets."""
        self._check_compatible(other)
        merged = self._with_bits(self._bits | other._bits, 0)
        merged._items_added = round(merged.estimated_cardinality())
        return merged

    def __and__(self, other: BloomFilter) -> BloomFilter:
        """Intersection: a superset approximation of the true intersection.

        Bits set by different items in each filter can coincide, so the result
        may have a *higher* false-positive rate than a filter built from the
        true intersection. It still has no false negatives.
        """
        self._check_compatible(other)
        merged = self._with_bits(self._bits & other._bits, 0)
        estimate = merged.estimated_cardinality()
        merged._items_added = 0 if math.isinf(estimate) else round(estimate)
        return merged

    # -- serialisation ----------------------------------------------------

    def to_bytes(self) -> bytes:
        header = self._HEADER.pack(
            self._MAGIC,
            self._VERSION,
            self.num_bits,
            self._num_hashes,
            self._seed,
            self._items_added,
        )
        return header + self._bits.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes) -> BloomFilter:
        if len(data) < cls._HEADER.size:
            raise ValueError("data too short for a Bloom filter header")
        magic, version, num_bits, num_hashes, seed, items_added = cls._HEADER.unpack_from(data)
        if magic != cls._MAGIC:
            raise ValueError("not a serialised BloomFilter (bad magic)")
        if version != cls._VERSION:
            raise ValueError(f"unsupported BloomFilter format version {version}")
        bloom = cls(num_bits, num_hashes, seed=seed)
        bloom._bits = BitArray.from_bytes(num_bits, data[cls._HEADER.size :])
        bloom._items_added = items_added
        return bloom

    def __repr__(self) -> str:
        return (
            f"BloomFilter(num_bits={self.num_bits}, num_hashes={self._num_hashes}, "
            f"items_added={self._items_added}, fill_ratio={self.fill_ratio:.3f})"
        )


class ScalableBloomFilter:
    """A Bloom filter that grows instead of degrading (Almeida et al., 2007).

    A fixed filter's error rate climbs past its target once it holds more than
    ``capacity`` items. This variant chains *stages*: when the newest stage is
    full, it appends a larger one (``growth`` times the capacity) with a
    tighter error rate (multiplied by ``tightening``). The compound error rate
    is bounded by a geometric series:

        P <= p0 * (1 + r + r^2 + ...) = p0 / (1 - r)

    so the first stage is given ``p0 = error_rate * (1 - r)`` and the whole
    structure stays under ``error_rate`` no matter how many stages it grows.
    The trade-off: lookups probe every stage, so they slow down logarithmically
    with the number of items.
    """

    def __init__(
        self,
        initial_capacity: int = 1_000,
        error_rate: float = 0.01,
        *,
        growth: int = 2,
        tightening: float = 0.85,
        seed: int = 0,
    ) -> None:
        if initial_capacity < 1:
            raise ValueError("initial_capacity must be at least 1")
        if not 0.0 < error_rate < 1.0:
            raise ValueError("error_rate must be strictly between 0 and 1")
        if growth < 1:
            raise ValueError("growth must be at least 1")
        if not 0.0 < tightening < 1.0:
            raise ValueError("tightening must be strictly between 0 and 1")
        self._initial_capacity = initial_capacity
        self._error_rate = error_rate
        self._growth = growth
        self._tightening = tightening
        self._seed = seed
        self._stages: list[tuple[BloomFilter, int]] = []
        self._add_stage()

    def _add_stage(self) -> None:
        level = len(self._stages)
        capacity = self._initial_capacity * self._growth**level
        stage_error = self._error_rate * (1 - self._tightening) * self._tightening**level
        # A distinct seed per stage keeps their hash families independent.
        stage = BloomFilter.from_capacity(capacity, stage_error, seed=(self._seed + level) & ((1 << 64) - 1))
        self._stages.append((stage, capacity))

    def add(self, item: Hashable) -> bool:
        """Insert ``item``; return ``True`` if it was definitely new."""
        if item in self:
            return False
        stage, capacity = self._stages[-1]
        if stage.items_added >= capacity:
            self._add_stage()
            stage, _ = self._stages[-1]
        stage.add(item)
        return True

    def update(self, items: Iterable[Hashable]) -> None:
        for item in items:
            self.add(item)

    def __contains__(self, item: Hashable) -> bool:
        # Newest stages hold the most items, so check them first.
        return any(item in stage for stage, _ in reversed(self._stages))

    def __len__(self) -> int:
        """Number of distinct items accepted (exact count of ``add`` returning True)."""
        return sum(stage.items_added for stage, _ in self._stages)

    @property
    def num_stages(self) -> int:
        return len(self._stages)

    @property
    def num_bits(self) -> int:
        return sum(stage.num_bits for stage, _ in self._stages)

    @property
    def error_bound(self) -> float:
        return self._error_rate

    def estimated_fpr(self) -> float:
        """Compound rate: probability that *any* stage yields a false positive."""
        miss_all = 1.0
        for stage, _ in self._stages:
            miss_all *= 1.0 - stage.estimated_fpr()
        return 1.0 - miss_all

    def __repr__(self) -> str:
        return (
            f"ScalableBloomFilter(items={len(self)}, stages={self.num_stages}, "
            f"num_bits={self.num_bits}, error_bound={self._error_rate})"
        )
