"""Reproducible experiments that measure each sketch against its theory.

Every experiment is a pure function of its arguments (including ``seed``) and
returns plain dataclasses, so the CLI, the tests and any notebook can share
them without parsing text output.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import accumulate

from sketches.bloom import BloomFilter, optimal_parameters, theoretical_fpr
from sketches.count_min import CountMinSketch


def _members(count: int, start: int = 0) -> list[str]:
    return [f"member-{i}" for i in range(start, start + count)]


def _probes(count: int) -> list[str]:
    # A disjoint namespace guarantees every probe is a true negative, so any
    # "present" answer is by definition a false positive.
    return [f"probe-{i}" for i in range(count)]


def _measured_fpr(bloom: BloomFilter, probes: Sequence[str]) -> float:
    return sum(probe in bloom for probe in probes) / len(probes)


@dataclass(frozen=True)
class BloomTrial:
    target_rate: float
    num_bits: int
    num_hashes: int
    bits_per_item: float
    theoretical_rate: float
    empirical_rate: float


def run_bloom_accuracy(
    error_rates: Sequence[float],
    *,
    capacity: int = 10_000,
    probes: int = 50_000,
    seed: int = 0,
) -> list[BloomTrial]:
    """Fill a filter to capacity for each target rate and measure its FPR."""
    if probes < 1:
        raise ValueError("probes must be at least 1")
    members = _members(capacity)
    probe_items = _probes(probes)
    trials = []
    for rate in error_rates:
        params = optimal_parameters(capacity, rate)
        bloom = BloomFilter(params.num_bits, params.num_hashes, seed=seed)
        bloom.update(members)
        trials.append(
            BloomTrial(
                target_rate=rate,
                num_bits=params.num_bits,
                num_hashes=params.num_hashes,
                bits_per_item=params.bits_per_item,
                theoretical_rate=theoretical_fpr(params.num_bits, params.num_hashes, capacity),
                empirical_rate=_measured_fpr(bloom, probe_items),
            )
        )
    return trials


@dataclass(frozen=True)
class LoadTrial:
    load_factor: float
    items: int
    theoretical_rate: float
    estimated_rate: float
    empirical_rate: float


def run_bloom_overload(
    *,
    error_rate: float = 0.01,
    capacity: int = 5_000,
    load_factors: Sequence[float] = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0),
    probes: int = 20_000,
    seed: int = 0,
) -> list[LoadTrial]:
    """Show how the FPR degrades as one filter is filled past its capacity."""
    if probes < 1:
        raise ValueError("probes must be at least 1")
    if list(load_factors) != sorted(load_factors) or min(load_factors, default=1) <= 0:
        raise ValueError("load_factors must be positive and ascending")
    bloom = BloomFilter.from_capacity(capacity, error_rate, seed=seed)
    probe_items = _probes(probes)
    inserted = 0
    trials = []
    for factor in load_factors:
        target = round(capacity * factor)
        bloom.update(_members(target - inserted, start=inserted))
        inserted = target
        trials.append(
            LoadTrial(
                load_factor=factor,
                items=inserted,
                theoretical_rate=theoretical_fpr(bloom.num_bits, bloom.num_hashes, inserted),
                estimated_rate=bloom.estimated_fpr(),
                empirical_rate=_measured_fpr(bloom, probe_items),
            )
        )
    return trials


def zipf_stream(length: int, distinct: int, skew: float, rng: random.Random) -> list[int]:
    """Draw ``length`` items from a Zipf(``skew``) distribution over ``distinct`` keys.

    Real frequency data (words, URLs, IPs) is heavily skewed; that is exactly
    where Count-Min shines and where conservative update helps most.
    """
    if length < 1 or distinct < 1:
        raise ValueError("length and distinct must be at least 1")
    if skew < 0:
        raise ValueError("skew must be non-negative")
    cumulative = list(accumulate(1.0 / (rank**skew) for rank in range(1, distinct + 1)))
    return rng.choices(range(distinct), cum_weights=cumulative, k=length)


@dataclass(frozen=True)
class CmsTrial:
    epsilon: float
    width: int
    depth: int
    conservative: bool
    mean_error: float
    max_error: int
    error_bound: float
    within_bound: float  # fraction of distinct items with error <= epsilon * N
    exact_fraction: float  # fraction of distinct items estimated exactly


def run_cms_accuracy(
    epsilons: Sequence[float],
    *,
    delta: float = 0.01,
    stream_length: int = 100_000,
    distinct: int = 20_000,
    skew: float = 1.1,
    seed: int = 0,
) -> list[CmsTrial]:
    """Measure standard and conservative Count-Min error on one Zipf stream."""
    stream = zipf_stream(stream_length, distinct, skew, random.Random(seed))
    truth = Counter(stream)
    trials = []
    for epsilon in epsilons:
        for conservative in (False, True):
            sketch = CountMinSketch.from_error(epsilon, delta, seed=seed, conservative=conservative)
            # Feed the stream item by item: conservative update is
            # order-sensitive, so pre-aggregated counts would flatter it.
            sketch.update(stream)
            errors = [sketch.estimate(item) - count for item, count in truth.items()]
            bound = sketch.error_bound()
            trials.append(
                CmsTrial(
                    epsilon=epsilon,
                    width=sketch.width,
                    depth=sketch.depth,
                    conservative=conservative,
                    mean_error=sum(errors) / len(errors),
                    max_error=max(errors),
                    error_bound=bound,
                    within_bound=sum(error <= bound for error in errors) / len(errors),
                    exact_fraction=sum(error == 0 for error in errors) / len(errors),
                )
            )
    return trials
