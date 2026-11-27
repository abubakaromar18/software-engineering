import math

import pytest

from sketches.bloom import BloomFilter, ScalableBloomFilter, optimal_parameters, theoretical_fpr


def members(n, prefix="m"):
    return [f"{prefix}-{i}" for i in range(n)]


class TestParameters:
    def test_textbook_values(self):
        # 1% at 1M items is the classic "~9.6 bits per item, 7 hashes".
        params = optimal_parameters(1_000_000, 0.01)
        assert params.num_hashes == 7
        assert 9.58 < params.bits_per_item < 9.59

    def test_tighter_rate_needs_more_bits(self):
        loose = optimal_parameters(1000, 0.1)
        tight = optimal_parameters(1000, 0.001)
        assert tight.num_bits > loose.num_bits and tight.num_hashes > loose.num_hashes

    @pytest.mark.parametrize("capacity, rate", [(0, 0.1), (10, 0.0), (10, 1.0)])
    def test_invalid(self, capacity, rate):
        with pytest.raises(ValueError):
            optimal_parameters(capacity, rate)

    def test_theoretical_fpr_matches_target_at_capacity(self):
        params = optimal_parameters(5000, 0.02)
        assert theoretical_fpr(params.num_bits, params.num_hashes, 5000) == pytest.approx(0.02, rel=0.05)
        assert theoretical_fpr(params.num_bits, params.num_hashes, 0) == 0.0


class TestBloomFilter:
    def test_no_false_negatives(self):
        bloom = BloomFilter.from_capacity(2000, 0.01)
        items = members(2000)
        bloom.update(items)
        assert all(item in bloom for item in items)

    def test_empty_filter_contains_nothing(self):
        bloom = BloomFilter.from_capacity(100, 0.01)
        assert "anything" not in bloom
        assert bloom.fill_ratio == 0.0

    def test_mixed_item_types(self):
        bloom = BloomFilter.from_capacity(100, 0.001)
        bloom.update(["a", b"a", 42])
        assert "a" in bloom and b"a" in bloom and 42 in bloom
        assert "42" not in bloom

    def test_add_reports_novelty_and_counts_distinct(self):
        bloom = BloomFilter.from_capacity(100, 0.001)
        assert bloom.add("x") is True
        assert bloom.add("x") is False
        assert bloom.items_added == 1

    def test_measured_fpr_close_to_target(self):
        bloom = BloomFilter.from_capacity(5000, 0.02, seed=7)
        bloom.update(members(5000))
        probes = members(20_000, prefix="probe")
        rate = sum(p in bloom for p in probes) / len(probes)
        assert 0.012 < rate < 0.03
        assert bloom.estimated_fpr() == pytest.approx(0.02, rel=0.15)

    def test_fill_ratio_near_half_at_capacity(self):
        bloom = BloomFilter.from_capacity(5000, 0.01)
        bloom.update(members(5000))
        assert 0.45 < bloom.fill_ratio < 0.55

    def test_cardinality_estimate(self):
        bloom = BloomFilter.from_capacity(10_000, 0.01)
        bloom.update(members(3000))
        assert bloom.estimated_cardinality() == pytest.approx(3000, rel=0.03)

    def test_saturated_cardinality_is_infinite(self):
        bloom = BloomFilter(8, 1)
        bloom.update(range(200))
        assert math.isinf(bloom.estimated_cardinality())

    def test_union_equals_inserting_both(self):
        a = BloomFilter.from_capacity(1000, 0.01)
        b = BloomFilter.from_capacity(1000, 0.01)
        both = BloomFilter.from_capacity(1000, 0.01)
        a.update(members(300, "a"))
        b.update(members(300, "b"))
        both.update(members(300, "a") + members(300, "b"))
        union = a | b
        assert union.to_bytes()[BloomFilter._HEADER.size :] == both.to_bytes()[BloomFilter._HEADER.size :]  # identical bits
        assert union.items_added == pytest.approx(600, rel=0.05)

    def test_intersection_keeps_common_items(self):
        a = BloomFilter.from_capacity(1000, 0.01)
        b = BloomFilter.from_capacity(1000, 0.01)
        a.update(members(200, "shared") + members(200, "a"))
        b.update(members(200, "shared") + members(200, "b"))
        common = a & b
        assert all(item in common for item in members(200, "shared"))
        assert sum(item in common for item in members(200, "a")) < 20

    def test_incompatible_filters_rejected(self):
        with pytest.raises(ValueError):
            BloomFilter(100, 3) | BloomFilter(100, 4)
        with pytest.raises(ValueError):
            BloomFilter(100, 3, seed=1) & BloomFilter(100, 3, seed=2)
        with pytest.raises(TypeError):
            BloomFilter(100, 3) | object()

    def test_serialisation_round_trip(self):
        bloom = BloomFilter.from_capacity(500, 0.01, seed=99)
        bloom.update(members(400))
        restored = BloomFilter.from_bytes(bloom.to_bytes())
        assert (restored.num_bits, restored.num_hashes, restored.seed, restored.items_added) == (
            bloom.num_bits, bloom.num_hashes, 99, 400,
        )
        assert all(item in restored for item in members(400))

    @pytest.mark.parametrize(
        "data",
        [b"short", b"XXXX" + bytes(40), BloomFilter(16, 2).to_bytes()[:-1]],
    )
    def test_corrupt_bytes_rejected(self, data):
        with pytest.raises(ValueError):
            BloomFilter.from_bytes(data)

    def test_unknown_version_rejected(self):
        data = bytearray(BloomFilter(16, 2).to_bytes())
        data[4] = 9
        with pytest.raises(ValueError, match="version"):
            BloomFilter.from_bytes(bytes(data))

    @pytest.mark.parametrize("bits, hashes", [(0, 1), (10, 0)])
    def test_invalid_construction(self, bits, hashes):
        with pytest.raises(ValueError):
            BloomFilter(bits, hashes)

    def test_repr(self):
        assert "num_hashes=3" in repr(BloomFilter(64, 3))


class TestScalableBloomFilter:
    def test_grows_and_keeps_every_item(self):
        sbf = ScalableBloomFilter(initial_capacity=100, error_rate=0.01)
        items = members(2000)
        sbf.update(items)
        assert sbf.num_stages > 1
        assert all(item in sbf for item in items)

    def test_len_counts_distinct_items(self):
        sbf = ScalableBloomFilter(initial_capacity=50)
        assert sbf.add("a") is True
        assert sbf.add("a") is False
        sbf.update(members(120))
        assert len(sbf) == 121

    def test_error_rate_stays_bounded_when_growing(self):
        sbf = ScalableBloomFilter(initial_capacity=200, error_rate=0.02, seed=3)
        sbf.update(members(5000))
        probes = members(20_000, prefix="probe")
        measured = sum(p in sbf for p in probes) / len(probes)
        assert measured < 0.02
        assert sbf.estimated_fpr() < sbf.error_bound

    def test_fixed_filter_overfilled_does_much_worse(self):
        fixed = BloomFilter.from_capacity(200, 0.02, seed=3)
        fixed.update(members(5000))
        assert fixed.estimated_fpr() > 0.5

    def test_stage_capacities_grow_geometrically(self):
        sbf = ScalableBloomFilter(initial_capacity=10, growth=3)
        sbf.update(members(10 + 30 + 1))
        assert sbf.num_stages == 3

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"initial_capacity": 0},
            {"error_rate": 1.5},
            {"growth": 0},
            {"tightening": 1.0},
        ],
    )
    def test_invalid_configuration(self, kwargs):
        with pytest.raises(ValueError):
            ScalableBloomFilter(**kwargs)

    def test_repr(self):
        assert "stages=1" in repr(ScalableBloomFilter())
