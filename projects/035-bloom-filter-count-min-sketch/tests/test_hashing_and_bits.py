import pytest

from sketches.bitarray import BitArray
from sketches.hashing import encode, hash_pair, indexes


class TestEncode:
    def test_types_are_distinct(self):
        assert len({encode("1"), encode(b"1"), encode(1)}) == 3

    def test_unicode_round_trip_is_stable(self):
        assert encode("café") == b"s" + "café".encode()

    @pytest.mark.parametrize("bad", [True, 1.5, None, ("a",)])
    def test_rejects_unsupported_types(self, bad):
        with pytest.raises(TypeError):
            encode(bad)


class TestHashing:
    def test_deterministic_across_calls(self):
        assert hash_pair("x") == hash_pair("x")

    def test_seed_changes_family(self):
        assert hash_pair("x", seed=1) != hash_pair("x", seed=2)

    def test_second_hash_is_odd(self):
        assert all(hash_pair(i)[1] % 2 == 1 for i in range(200))

    def test_indexes_are_in_range_and_counted(self):
        result = list(indexes("item", 7, 13))
        assert len(result) == 7
        assert all(0 <= i < 13 for i in result)

    def test_indexes_spread_roughly_uniformly(self):
        buckets = [0] * 10
        for i in range(10_000):
            buckets[next(indexes(i, 1, 10))] += 1
        # Each bucket expects 1000; allow a generous ±15%.
        assert all(850 <= b <= 1150 for b in buckets)

    @pytest.mark.parametrize("count, modulus", [(0, 10), (3, 0)])
    def test_invalid_arguments(self, count, modulus):
        with pytest.raises(ValueError):
            list(indexes("x", count, modulus))

    def test_seed_out_of_range(self):
        with pytest.raises(ValueError):
            hash_pair("x", seed=-1)


class TestBitArray:
    def test_starts_empty(self):
        bits = BitArray(20)
        assert len(bits) == 20
        assert bits.count() == 0
        assert not any(bits[i] for i in range(20))

    def test_set_reports_previous_state(self):
        bits = BitArray(9)
        assert bits.set(8) is False
        assert bits.set(8) is True
        assert bits[8] and bits.count() == 1

    def test_bounds_checked(self):
        bits = BitArray(8)
        with pytest.raises(IndexError):
            bits[8]
        with pytest.raises(IndexError):
            bits.set(-1)

    def test_or_and(self):
        a, b = BitArray(16), BitArray(16)
        for i in (1, 2, 3):
            a.set(i)
        for i in (3, 4):
            b.set(i)
        assert [i for i in range(16) if (a | b)[i]] == [1, 2, 3, 4]
        assert [i for i in range(16) if (a & b)[i]] == [3]

    def test_size_mismatch(self):
        with pytest.raises(ValueError):
            BitArray(8) | BitArray(9)

    def test_bytes_round_trip(self):
        bits = BitArray(13)
        for i in (0, 5, 12):
            bits.set(i)
        assert BitArray.from_bytes(13, bits.to_bytes()) == bits

    def test_from_bytes_validates(self):
        with pytest.raises(ValueError):
            BitArray.from_bytes(13, b"\x00")
        with pytest.raises(ValueError):
            BitArray.from_bytes(13, b"\x00\x01")  # padding bit set

    def test_unhashable(self):
        with pytest.raises(TypeError):
            hash(BitArray(4))

    def test_invalid_size(self):
        with pytest.raises(ValueError):
            BitArray(0)
