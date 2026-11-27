import math
import random
from collections import Counter

import pytest

from sketches.count_min import CountMinSketch, TopK
from sketches.experiments import zipf_stream


@pytest.fixture
def stream():
    return zipf_stream(20_000, 5_000, 1.1, random.Random(1))


class TestSizing:
    def test_from_error(self):
        sketch = CountMinSketch.from_error(0.01, 0.01)
        assert sketch.width == math.ceil(math.e / 0.01)
        assert sketch.depth == math.ceil(math.log(100))
        assert sketch.epsilon <= 0.01 and sketch.delta <= 0.01
        assert sketch.memory_bytes == sketch.width * sketch.depth * 8

    @pytest.mark.parametrize("epsilon, delta", [(0, 0.1), (0.1, 0), (1, 0.1), (0.1, 1)])
    def test_invalid_error(self, epsilon, delta):
        with pytest.raises(ValueError):
            CountMinSketch.from_error(epsilon, delta)

    @pytest.mark.parametrize("width, depth", [(0, 1), (1, 0)])
    def test_invalid_dimensions(self, width, depth):
        with pytest.raises(ValueError):
            CountMinSketch(width, depth)


class TestCountMin:
    def test_exact_without_collisions(self):
        sketch = CountMinSketch(10_000, 4)
        sketch.add("a", 5)
        sketch.add("b")
        assert sketch["a"] == 5 and sketch.estimate("b") == 1 and sketch["zzz"] == 0
        assert sketch.total == 6

    def test_add_returns_new_estimate(self):
        sketch = CountMinSketch(1000, 3)
        assert sketch.add("x", 3) == 3
        assert sketch.add("x") == 4

    def test_negative_counts_rejected(self):
        with pytest.raises(ValueError):
            CountMinSketch(10, 2).add("x", -1)

    @pytest.mark.parametrize("conservative", [False, True])
    def test_never_underestimates(self, stream, conservative):
        sketch = CountMinSketch(64, 3, conservative=conservative)  # tiny: many collisions
        sketch.update(stream)
        truth = Counter(stream)
        assert all(sketch.estimate(item) >= count for item, count in truth.items())

    @pytest.mark.parametrize("conservative", [False, True])
    def test_error_bound_holds_with_probability(self, stream, conservative):
        sketch = CountMinSketch.from_error(0.005, 0.01, seed=5, conservative=conservative)
        sketch.update(stream)
        truth = Counter(stream)
        bound = sketch.error_bound()
        within = sum(sketch.estimate(i) - c <= bound for i, c in truth.items()) / len(truth)
        assert within >= 1 - sketch.delta

    def test_conservative_is_never_worse(self, stream):
        standard = CountMinSketch(200, 4, seed=2)
        conservative = CountMinSketch(200, 4, seed=2, conservative=True)
        standard.update(stream)
        conservative.update(stream)
        truth = Counter(stream)
        assert all(conservative[i] <= standard[i] for i in truth)
        assert sum(conservative[i] for i in truth) < sum(standard[i] for i in truth)

    def test_merge_equals_single_sketch(self, stream):
        half = len(stream) // 2
        left, right, whole = (CountMinSketch(300, 4, seed=8) for _ in range(3))
        left.update(stream[:half])
        right.update(stream[half:])
        whole.update(stream)
        left.merge(right)
        assert left.total == whole.total
        assert all(left[i] == whole[i] for i in set(stream))

    def test_merge_rejects_incompatible(self):
        with pytest.raises(ValueError):
            CountMinSketch(10, 2).merge(CountMinSketch(11, 2))
        with pytest.raises(TypeError):
            CountMinSketch(10, 2).merge("nope")

    def test_counter_overflow_guarded_by_unsigned_storage(self):
        sketch = CountMinSketch(4, 1)
        with pytest.raises(OverflowError):
            sketch.add("x", 2**64)

    def test_repr(self):
        assert "conservative" in repr(CountMinSketch(4, 1, conservative=True))


class TestTopK:
    def test_finds_heavy_hitters(self, stream):
        tracker = TopK(5, CountMinSketch.from_error(0.001, 0.01, conservative=True))
        tracker.update(stream)
        expected = [item for item, _ in Counter(stream).most_common(5)]
        assert [item for item, _ in tracker.items()] == expected

    def test_estimates_are_upper_bounds(self, stream):
        tracker = TopK(10, CountMinSketch(500, 4))
        tracker.update(stream)
        truth = Counter(stream)
        assert all(estimate >= truth[item] for item, estimate in tracker.items())

    def test_table_size_bounded_by_k(self):
        tracker = TopK(3, CountMinSketch(1000, 3))
        tracker.update(range(100))
        assert len(tracker.items()) == 3

    def test_invalid_k(self):
        with pytest.raises(ValueError):
            TopK(0, CountMinSketch(10, 2))
