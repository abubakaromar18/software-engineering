"""Properties of run-length encoding and varints.

The core law for any codec is the round trip. It is necessary but not
sufficient (``encode = decode = identity`` passes it), so it is paired with
properties that pin the format down: canonical output, compactness, and
rejection of malformed input.
"""

import re

import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st

from pbtlab import strategies as pst
from pbtlab.encoding import (
    DecodeError,
    decode_svarint,
    decode_svarints,
    decode_varint,
    encode_svarint,
    encode_svarints,
    encode_varint,
    rle_decode,
    rle_encode,
    unzigzag,
    zigzag,
)

# ------------------------------------------------------------------ RLE


@given(pst.rle_text)
@example("0")  # regression: unescaped digit collided with the count
@example("a" * 10)  # regression: two-digit count read as one digit
@example("\\")
def test_rle_round_trip(text):
    assert rle_decode(rle_encode(text)) == text


@given(pst.rle_text)
def test_rle_runs_are_maximal(text):
    """No two consecutive runs use the same character: the encoding is canonical."""
    runs = re.findall(r"(\d+)(\\.|.)", rle_encode(text), flags=re.DOTALL)
    chars = [ch[-1] for _, ch in runs]
    assert all(a != b for a, b in zip(chars, chars[1:], strict=False))
    assert all(not count.startswith("0") for count, _ in runs)


@given(st.text(alphabet="xyz", min_size=1), st.integers(min_value=2, max_value=50))
def test_rle_compresses_long_runs(seed, repeat):
    """Repeating every character makes the encoding no longer than the run count suggests."""
    text = "".join(ch * repeat for ch in seed)
    assert len(rle_encode(text)) <= len(seed) * (len(str(repeat * len(seed))) + 1)


@given(st.text(alphabet="0123456789ab\\", max_size=12))
@example("999999999999a")  # regression: decompression bomb, found by this fuzz test
def test_rle_decode_never_crashes_unexpectedly(garbage):
    """Fuzzing: arbitrary input either decodes or raises DecodeError, nothing else."""
    try:
        decoded = rle_decode(garbage)
    except DecodeError:
        return
    assert rle_decode(rle_encode(decoded)) == decoded


@pytest.mark.parametrize(
    ("text", "encoded"),
    [("", ""), ("aaab", "3a1b"), ("1111", "4\\1"), ("a\\b", "1a1\\\\1b")],
)
def test_rle_known_encodings(text, encoded):
    assert rle_encode(text) == encoded


@given(st.integers(min_value=1, max_value=100), st.integers(min_value=0, max_value=100))
def test_rle_decode_enforces_output_limit(count, limit):
    encoded = f"{count}a"
    if count <= limit:
        assert rle_decode(encoded, max_decoded=limit) == "a" * count
    else:
        with pytest.raises(DecodeError, match="max_decoded"):
            rle_decode(encoded, max_decoded=limit)


@pytest.mark.parametrize("bad", ["a", "3", "03a", "3\\", "31"])
def test_rle_rejects_malformed(bad):
    with pytest.raises(DecodeError):
        rle_decode(bad)


# -------------------------------------------------------------- varints


@given(st.integers(min_value=0))
def test_varint_round_trip(n):
    data = encode_varint(n)
    assert decode_varint(data) == (n, len(data))


@given(st.integers(min_value=0))
def test_varint_length_is_ceil_bits_over_seven(n):
    assert len(encode_varint(n)) == max(1, -(-n.bit_length() // 7))


@given(st.integers(min_value=0))
def test_varint_only_last_byte_lacks_continuation_bit(n):
    data = encode_varint(n)
    assert all(b & 0x80 for b in data[:-1])
    assert not data[-1] & 0x80


@given(st.integers())
@example(2**63)  # regression: fixed-width zigzag broke outside int64
@example(-(2**63) - 1)
def test_zigzag_is_a_bijection_onto_naturals(n):
    z = zigzag(n)
    assert z >= 0
    assert unzigzag(z) == n


@given(st.integers(min_value=0))
def test_unzigzag_then_zigzag(z):
    assert zigzag(unzigzag(z)) == z


@given(st.integers(min_value=-(2**20), max_value=2**20))
def test_zigzag_keeps_small_magnitudes_small(n):
    assert zigzag(n) <= 2 * abs(n)


@given(st.lists(st.integers()))
def test_svarint_stream_round_trip(values):
    assert decode_svarints(encode_svarints(values)) == values


@given(st.integers(), st.binary(max_size=8))
def test_svarint_decode_reports_where_it_stopped(n, trailing):
    data = encode_svarint(n) + trailing
    value, pos = decode_svarint(data)
    assert value == n
    assert data[pos:] == trailing


@given(st.integers(min_value=0))
def test_truncated_varint_is_rejected(n):
    data = encode_varint(n)
    assume(len(data) > 1)
    with pytest.raises(DecodeError, match="truncated"):
        decode_varint(data[:-1])


@given(st.binary(max_size=10))
def test_decode_varint_fuzz(data):
    """Any bytes either decode canonically or raise DecodeError."""
    try:
        value, pos = decode_varint(data)
    except DecodeError:
        return
    assert encode_varint(value) == data[:pos]


def test_non_canonical_varint_is_rejected():
    with pytest.raises(DecodeError, match="non-canonical"):
        decode_varint(b"\x80\x00")


def test_unsigned_varint_rejects_negative():
    with pytest.raises(ValueError, match="encode_svarint"):
        encode_varint(-1)


def test_known_varints():
    assert encode_varint(0) == b"\x00"
    assert encode_varint(300) == b"\xac\x02"  # the example from the protobuf docs
    assert encode_svarint(-1) == b"\x01"
