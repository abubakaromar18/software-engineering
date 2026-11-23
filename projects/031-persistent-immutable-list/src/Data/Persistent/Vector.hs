-- |
-- Module      : Data.Persistent.Vector
-- Description : A persistent vector with O(log32 n) indexing and updates.
--
-- An immutable, indexable sequence backed by a 32-way bit-partitioned trie
-- (the design behind Clojure's and Scala's vectors). Old versions remain
-- valid after every operation and share almost all of their structure with
-- new ones:
--
-- * 'lookup' \/ '(!?)': O(log32 n), copies nothing.
-- * 'update' \/ 'adjust': O(log32 n), copies one root-to-leaf path.
-- * 'snoc' \/ 'unsnoc': amortised O(1); copies the tail, and one path in
--   every 32 calls.
-- * 'length' \/ 'null' \/ 'last': O(1).
--
-- @log32@ of a billion is 6, so \"logarithmic\" here means a handful of
-- pointer hops in practice.
--
-- > import qualified Data.Persistent.Vector as V
module Data.Persistent.Vector
  ( Vector

    -- * Construction
  , empty
  , singleton
  , fromList
  , snoc
  , (|>)

    -- * Queries
  , length
  , null
  , lookup
  , (!?)
  , last

    -- * Updates
  , update
  , adjust
  , unsnoc
  ) where

import Data.Persistent.Vector.Internal (Vector, adjust, empty, fromList, lookup, snoc, unsnoc)
import qualified Data.Persistent.Vector.Internal as I
import Prelude hiding (last, length, lookup, null)

-- | A one-element vector.
singleton :: a -> Vector a
singleton = snoc empty

-- | Infix 'snoc'.
(|>) :: Vector a -> a -> Vector a
(|>) = snoc

infixl 5 |>

-- | Number of elements. O(1).
length :: Vector a -> Int
length = I.vSize

-- | Is the vector empty? O(1).
null :: Vector a -> Bool
null v = length v == 0

-- | Flipped 'lookup', matching @Data.List.!?@.
(!?) :: Vector a -> Int -> Maybe a
v !? i = lookup i v

infixl 9 !?

-- | Last element, if any. O(1): it is always in the tail.
last :: Vector a -> Maybe a
last v = lookup (length v - 1) v

-- | Replace the element at an index. Out-of-range indices return the
-- vector unchanged, as in "Data.Sequence". O(log32 n).
update :: Int -> a -> Vector a -> Vector a
update i x = adjust (const x) i
