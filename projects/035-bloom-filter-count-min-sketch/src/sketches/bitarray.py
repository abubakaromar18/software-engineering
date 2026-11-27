"""A fixed-size, compact bit array backed by a ``bytearray``.

A Bloom filter's whole value is memory efficiency, so storing one bit per
Python ``bool`` (28+ bytes each) would defeat the point. This class packs
eight bits per byte and supports the bitwise set operations Bloom filters
need for union and intersection.
"""

from __future__ import annotations


class BitArray:
    """Fixed-length array of bits, all initially zero."""

    __slots__ = ("_size", "_bytes")

    def __init__(self, size: int) -> None:
        if size < 1:
            raise ValueError("size must be at least 1")
        self._size = size
        self._bytes = bytearray((size + 7) // 8)

    @classmethod
    def from_bytes(cls, size: int, data: bytes) -> BitArray:
        """Rebuild an array of ``size`` bits from :meth:`to_bytes` output."""
        array = cls(size)
        if len(data) != len(array._bytes):
            raise ValueError(f"expected {len(array._bytes)} bytes for {size} bits, got {len(data)}")
        trailing = len(data) * 8 - size
        # Bits are stored MSB-first, so padding occupies the low bits of the last byte.
        if data[-1] & ((1 << trailing) - 1):
            raise ValueError("padding bits beyond size must be zero")
        array._bytes[:] = data
        return array

    def __len__(self) -> int:
        return self._size

    def _locate(self, index: int) -> tuple[int, int]:
        if not 0 <= index < self._size:
            raise IndexError(f"bit index {index} out of range for size {self._size}")
        # Bit 0 is the most significant bit of byte 0; padding sits at the end.
        return index >> 3, 0x80 >> (index & 7)

    def __getitem__(self, index: int) -> bool:
        byte, mask = self._locate(index)
        return bool(self._bytes[byte] & mask)

    def set(self, index: int) -> bool:
        """Set bit ``index`` and return whether it was previously set."""
        byte, mask = self._locate(index)
        was_set = bool(self._bytes[byte] & mask)
        self._bytes[byte] |= mask
        return was_set

    def count(self) -> int:
        """Return the number of set bits (population count)."""
        return int.from_bytes(self._bytes, "big").bit_count()

    def _check_compatible(self, other: BitArray) -> None:
        if not isinstance(other, BitArray):
            raise TypeError("operand must be a BitArray")
        if other._size != self._size:
            raise ValueError("bit arrays must have the same size")

    def __or__(self, other: BitArray) -> BitArray:
        self._check_compatible(other)
        result = BitArray(self._size)
        result._bytes[:] = bytes(a | b for a, b in zip(self._bytes, other._bytes))
        return result

    def __and__(self, other: BitArray) -> BitArray:
        self._check_compatible(other)
        result = BitArray(self._size)
        result._bytes[:] = bytes(a & b for a, b in zip(self._bytes, other._bytes))
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BitArray):
            return NotImplemented
        return self._size == other._size and self._bytes == other._bytes

    # Mutable container with value equality: explicitly unhashable.
    __hash__ = None  # type: ignore[assignment]

    def to_bytes(self) -> bytes:
        return bytes(self._bytes)

    def __repr__(self) -> str:
        return f"BitArray(size={self._size}, set={self.count()})"
