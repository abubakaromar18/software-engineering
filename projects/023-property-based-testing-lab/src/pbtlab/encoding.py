"""Two small, lossless encodings: run-length text and LEB128 varints.

Both are designed around a round-trip contract, ``decode(encode(x)) == x``,
which is exactly the kind of law property-based tests check well.
"""

from __future__ import annotations

from collections.abc import Iterable

# --------------------------------------------------------------------------
# Run-length encoding
#
# Format: a sequence of runs, each ``<count><char>`` where ``count`` is one
# or more decimal digits (no leading zeros, >= 1). Because counts are digits,
# a literal digit or backslash in the data is escaped as ``\<char>``.
#
#   "aaab"   -> "3a1b"
#   "1111"   -> "4\1"
#   "a\\b"   -> "1a1\\1b"
# --------------------------------------------------------------------------

_ESCAPE = "\\"

# Upper bound on decoded length. A 12-byte input like "999999999999a" would
# otherwise ask for a terabyte of memory: a decompression bomb. Callers that
# trust their input can raise the limit.
DEFAULT_MAX_DECODED = 1_000_000


class DecodeError(ValueError):
    """Raised when encoded input is malformed."""


def _needs_escape(ch: str) -> bool:
    return ch.isdigit() or ch == _ESCAPE


def rle_encode(text: str) -> str:
    """Run-length encode ``text``. Never fails; output is ASCII-safe for ASCII input."""
    parts: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        run_end = i
        while run_end < len(text) and text[run_end] == ch:
            run_end += 1
        escaped = _ESCAPE + ch if _needs_escape(ch) else ch
        parts.append(f"{run_end - i}{escaped}")
        i = run_end
    return "".join(parts)


def rle_decode(encoded: str, *, max_decoded: int = DEFAULT_MAX_DECODED) -> str:
    """Inverse of :func:`rle_encode`. Raises :class:`DecodeError` on bad input.

    Also raises :class:`DecodeError` if the output would exceed ``max_decoded``
    characters, so hostile input cannot exhaust memory.
    """
    out: list[str] = []
    produced = 0
    i = 0
    while i < len(encoded):
        start = i
        # str.isdigit() accepts things like '²'; int() does not, so be strict.
        while i < len(encoded) and encoded[i] in "0123456789":
            i += 1
        if i == start:
            raise DecodeError(f"expected a run count at position {start}")
        digits = encoded[start:i]
        if digits[0] == "0":
            raise DecodeError(f"run count {digits!r} at position {start} must be >= 1")
        if i >= len(encoded):
            raise DecodeError("input ends after a run count")
        ch = encoded[i]
        if ch == _ESCAPE:
            i += 1
            if i >= len(encoded):
                raise DecodeError("input ends after an escape character")
            ch = encoded[i]
        elif _needs_escape(ch):
            raise DecodeError(f"unescaped {ch!r} at position {i}")
        count = int(digits)
        produced += count
        if produced > max_decoded:
            raise DecodeError(f"decoded output exceeds max_decoded={max_decoded}")
        out.append(ch * count)
        i += 1
    return "".join(out)


# --------------------------------------------------------------------------
# Varints (unsigned LEB128, as used by protobuf, WebAssembly, DWARF)
#
# Seven payload bits per byte, least-significant group first; the high bit
# is set on every byte except the last. Signed integers are mapped onto
# unsigned ones with ZigZag (0, -1, 1, -2, ... -> 0, 1, 2, 3, ...) so small
# negative numbers stay short. Python ints are unbounded, so no 64-bit cap.
# --------------------------------------------------------------------------

_PAYLOAD = 0x7F
_CONTINUE = 0x80


def encode_varint(value: int) -> bytes:
    """Encode a non-negative integer of any size."""
    if value < 0:
        raise ValueError(f"unsigned varint cannot encode {value}; use encode_svarint")
    out = bytearray()
    while True:
        byte = value & _PAYLOAD
        value >>= 7
        if value:
            out.append(byte | _CONTINUE)
        else:
            out.append(byte)
            return bytes(out)


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode one varint starting at ``offset``; return ``(value, next_offset)``.

    Rejects truncated input and non-canonical (over-long) encodings such as
    ``b"\\x80\\x00"`` so that every integer has exactly one byte representation.
    """
    value = shift = 0
    pos = offset
    while True:
        if pos >= len(data):
            raise DecodeError(f"truncated varint starting at offset {offset}")
        byte = data[pos]
        pos += 1
        value |= (byte & _PAYLOAD) << shift
        shift += 7
        if not byte & _CONTINUE:
            if byte == 0 and pos - offset > 1:
                raise DecodeError(f"non-canonical varint at offset {offset}")
            return value, pos


def zigzag(value: int) -> int:
    """Map a signed int to unsigned: 0→0, -1→1, 1→2, -2→3, …"""
    return value * 2 if value >= 0 else -value * 2 - 1


def unzigzag(value: int) -> int:
    """Inverse of :func:`zigzag`."""
    return value >> 1 if value % 2 == 0 else -(value >> 1) - 1


def encode_svarint(value: int) -> bytes:
    """Encode a signed integer of any size using ZigZag + LEB128."""
    return encode_varint(zigzag(value))


def decode_svarint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Inverse of :func:`encode_svarint`."""
    raw, pos = decode_varint(data, offset)
    return unzigzag(raw), pos


def encode_svarints(values: Iterable[int]) -> bytes:
    """Concatenate signed varints; the format is self-delimiting."""
    return b"".join(encode_svarint(v) for v in values)


def decode_svarints(data: bytes) -> list[int]:
    """Decode a whole buffer produced by :func:`encode_svarints`."""
    values: list[int] = []
    pos = 0
    while pos < len(data):
        value, pos = decode_svarint(data, pos)
        values.append(value)
    return values
