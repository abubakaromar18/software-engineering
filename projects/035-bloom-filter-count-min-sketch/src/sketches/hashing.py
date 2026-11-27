"""Hashing shared by every sketch.

Both structures need ``k`` "independent" hash functions. Computing ``k``
cryptographic digests per operation is wasteful, so we use *enhanced double
hashing* (Dillinger & Manolios, 2004): derive two 64-bit values ``h1`` and
``h2`` from a single BLAKE2b digest and generate

    g_i(x) = h1 + i*h2 + (i**3 - i) / 6   (mod m)

Kirsch & Mitzenmacher showed that a Bloom filter built from this family has
the same asymptotic false-positive rate as one built from truly independent
hashes. The cubic term removes the clustering that plain double hashing
suffers when ``h2`` shares a factor with ``m``.

BLAKE2b is in the standard library, fast, and keyed, which gives each sketch
its own hash family via ``seed``. Python's built-in ``hash()`` is unsuitable:
it is randomised per process for ``str``, so a serialised filter would be
useless after a restart.
"""

from __future__ import annotations

from collections.abc import Iterator
from hashlib import blake2b
from typing import Union

Hashable = Union[str, bytes, int]

_MASK64 = (1 << 64) - 1


def encode(item: Hashable) -> bytes:
    """Return a canonical byte encoding of ``item``.

    A one-byte type tag keeps ``"1"``, ``b"1"`` and ``1`` distinct, so the
    sketches behave like a set of typed values rather than of byte strings.
    """
    # bool is a subclass of int; reject it to avoid True == 1 surprises.
    if isinstance(item, bool):
        raise TypeError("bool items are ambiguous; convert to int or str explicitly")
    if isinstance(item, str):
        return b"s" + item.encode("utf-8")
    if isinstance(item, bytes):
        return b"b" + item
    if isinstance(item, int):
        return b"i" + str(item).encode("ascii")
    raise TypeError(f"unsupported item type {type(item).__name__}; use str, bytes or int")


def hash_pair(item: Hashable, seed: int = 0) -> tuple[int, int]:
    """Return two 64-bit hashes of ``item`` from one keyed BLAKE2b digest."""
    if not 0 <= seed <= _MASK64:
        raise ValueError("seed must fit in an unsigned 64-bit integer")
    digest = blake2b(encode(item), digest_size=16, key=seed.to_bytes(8, "little")).digest()
    h1 = int.from_bytes(digest[:8], "little")
    # Force h2 odd so the probe sequence never degenerates to a single slot.
    h2 = int.from_bytes(digest[8:], "little") | 1
    return h1, h2


def indexes(item: Hashable, count: int, modulus: int, seed: int = 0) -> Iterator[int]:
    """Yield ``count`` positions in ``range(modulus)`` for ``item``."""
    if count < 1:
        raise ValueError("count must be at least 1")
    if modulus < 1:
        raise ValueError("modulus must be at least 1")
    h1, h2 = hash_pair(item, seed)
    for i in range(count):
        yield (h1 + i * h2 + (i * i * i - i) // 6) % modulus
