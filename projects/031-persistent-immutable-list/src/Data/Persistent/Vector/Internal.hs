{-# LANGUAGE DeriveTraversable #-}

-- |
-- Module      : Data.Persistent.Vector.Internal
-- Description : Representation and core algorithms of the persistent vector.
--
-- A bit-partitioned vector trie in the style of Clojure's @PersistentVector@:
--
-- * Elements live in 'Leaf' nodes of exactly 'width' elements, under a tree
--   of 'Branch' nodes with up to 'width' children each.
-- * The last, possibly partial, chunk is kept outside the tree in a /tail/
--   array, so 'snoc' usually touches only the tail.
-- * The index of an element spells out its path: each level of the tree
--   consumes 'bits' bits of the index, most significant first.
--
-- Updates use /path copying/: the nodes on the root-to-leaf path are copied
-- (at most @width@ pointers each) and every other subtree is shared with
-- the previous version. With @width = 32@ a vector of a million elements is
-- four levels deep, so an update copies four small arrays.
--
-- This module exposes the representation for tests, benchmarks and the
-- demo. It is not a stable API: use "Data.Persistent.Vector".
module Data.Persistent.Vector.Internal
  ( -- * Representation
    Vector (..)
  , Node (..)
  , bits
  , width
  , mask

    -- * Core operations
  , empty
  , fromList
  , snoc
  , unsnoc
  , lookup
  , adjust

    -- * Introspection
  , depth
  , tailOffset
  , invariantViolations
  ) where

import Data.Array (Array, bounds, elems, listArray, (!), (//))
import Data.Bits (shiftL, shiftR, (.&.))
import qualified Data.Foldable as F
import Data.Maybe (fromMaybe)
import Prelude hiding (lookup)

-- | Bits of the index consumed per tree level.
bits :: Int
bits = 5

-- | Branching factor: @2 ^ bits@.
width :: Int
width = 1 `shiftL` bits

-- | Mask selecting one level's worth of index bits.
mask :: Int
mask = width - 1

-- | A tree node. Leaves always hold exactly 'width' elements; branches hold
-- between 1 and 'width' children (the root may be empty).
data Node a
  = Branch !(Array Int (Node a))
  | Leaf !(Array Int a)
  deriving (Functor, Foldable, Traversable)

-- | A persistent vector.
data Vector a = Vector
  { vSize :: !Int
  -- ^ Number of elements.
  , vShift :: !Int
  -- ^ Index bit-offset at the root: @bits * (levels of branches)@. A tree
  -- whose root's children are leaves has shift 'bits'.
  , vRoot :: !(Node a)
  -- ^ Holds elements @[0, tailOffset)@.
  , vTail :: !(Array Int a)
  -- ^ Holds elements @[tailOffset, size)@; between 1 and 'width' elements
  -- unless the vector is empty.
  }
  deriving (Functor, Traversable)

-- Hand-written so that 'length' and 'null' are O(1) instead of a full fold.
instance Foldable Vector where
  foldr f z v = foldr f (foldr f z (vTail v)) (vRoot v)
  foldl' f z v = F.foldl' f (F.foldl' f z (vRoot v)) (vTail v)
  length = vSize
  null v = vSize v == 0

instance Eq a => Eq (Vector a) where
  v == w = length v == length w && F.toList v == F.toList w

instance Ord a => Ord (Vector a) where
  compare v w = compare (F.toList v) (F.toList w)

-- | Shows as @fromList [..]@, hiding the tree.
instance Show a => Show (Vector a) where
  showsPrec d v =
    showParen (d > 10) $ showString "fromList " . shows (F.toList v)

-- | Concatenation: repeated 'snoc' of the right operand. O(length w).
instance Semigroup (Vector a) where
  v <> w = F.foldl' snoc v w

instance Monoid (Vector a) where
  mempty = empty

------------------------------------------------------------------------------
-- Small immutable-array helpers. Arrays are always zero-based.

arrayOf :: [a] -> Array Int a
arrayOf xs = listArray (0, length xs - 1) xs

arrayLength :: Array Int a -> Int
arrayLength a = let (lo, hi) = bounds a in hi - lo + 1

-- | Copy with one slot replaced, or with one element appended when the
-- index is one past the end. Either way the original is untouched.
arraySet :: Int -> a -> Array Int a -> Array Int a
arraySet i x a
  | i == arrayLength a = arrayOf (elems a ++ [x])
  | otherwise = a // [(i, x)]

-- | The first @n@ slots.
arrayTake :: Int -> Array Int a -> Array Int a
arrayTake n = arrayOf . Prelude.take n . elems

------------------------------------------------------------------------------
-- Core operations

emptyBranch :: Node a
emptyBranch = Branch (arrayOf [])

-- | The empty vector.
empty :: Vector a
empty = Vector 0 bits emptyBranch (arrayOf [])

-- | Index of the first element stored in the tail.
tailOffset :: Int -> Int
tailOffset size
  | size < width = 0
  | otherwise = ((size - 1) `shiftR` bits) `shiftL` bits

-- | Number of branch levels above the leaves (1 for any vector that fits in
-- a single level of leaves).
depth :: Vector a -> Int
depth v = vShift v `div` bits

-- | Child slot selected by index @i@ at a node of the given shift.
slot :: Int -> Int -> Int
slot shift i = (i `shiftR` shift) .&. mask

-- | Append an element at the end. Amortised O(1): only one call in 'width'
-- touches the tree, and then only along one path.
snoc :: Vector a -> a -> Vector a
snoc v@(Vector size shift root tl) x
  | arrayLength tl < width = v {vSize = size + 1, vTail = arraySet (arrayLength tl) x tl}
  | rootOverflow =
      -- The tree is full at this depth: grow a new root above the old one.
      let root' = Branch (arrayOf [root, newPath shift tailLeaf])
       in Vector (size + 1) (shift + bits) root' (arrayOf [x])
  | otherwise = Vector (size + 1) shift (pushTail shift root) (arrayOf [x])
  where
    tailLeaf = Leaf tl
    -- After pushing the tail there will be (size >> bits) leaves; a tree of
    -- this shift has room for (1 << shift) of them.
    rootOverflow = (size `shiftR` bits) > (1 `shiftL` shift)

    -- Insert the full tail as the new right-most leaf, copying one path.
    pushTail level (Branch children) =
      let i = slot level (size - 1)
          child
            | level == bits = tailLeaf
            | i < arrayLength children = pushTail (level - bits) (children ! i)
            | otherwise = newPath (level - bits) tailLeaf
       in Branch (arraySet i child children)
    pushTail _ leaf@(Leaf _) = leaf -- unreachable: leaves sit at level 0

-- | Build from a finite list in O(n), bottom-up: cut the input into
-- 'width'-sized leaves, keep the last chunk as the tail, then group nodes 32
-- at a time until one root remains. This avoids the per-element tail copy
-- of repeated 'snoc' and yields exactly the same (canonical) shape.
fromList :: [a] -> Vector a
fromList xs = case chunksOf width xs of
  [] -> empty
  chunks ->
    let size = length xs
        leaves = map (Leaf . arrayOf) (init chunks)
        (shift, root) = buildTree bits leaves
     in Vector size shift root (arrayOf (Prelude.last chunks))
  where
    buildTree level nodes = case group nodes of
      [] -> (bits, emptyBranch)
      [single] -> (level, single)
      parents -> buildTree (level + bits) parents
    group = map (Branch . arrayOf) . chunksOf width

chunksOf :: Int -> [a] -> [[a]]
chunksOf _ [] = []
chunksOf k ys = let (front, back) = splitAt k ys in front : chunksOf k back

-- | A chain of single-child branches from @level@ down to the given leaf.
newPath :: Int -> Node a -> Node a
newPath 0 node = node
newPath level node = Branch (arrayOf [newPath (level - bits) node])

-- | Remove the last element. O(log32 n) worst case, O(1) usually.
unsnoc :: Vector a -> Maybe (Vector a, a)
unsnoc (Vector size shift root tl)
  | size == 0 = Nothing
  | size == 1 = Just (empty, lastElem)
  | arrayLength tl > 1 =
      Just (Vector (size - 1) shift root (arrayTake (arrayLength tl - 1) tl), lastElem)
  | otherwise =
      -- The tail empties: the right-most leaf moves out of the tree to
      -- become the new tail, and the tree may lose a level.
      let tl' = leafContaining shift root newLast
          (shift', root') = collapse shift (fromMaybe emptyBranch (popTail shift root))
       in Just (Vector (size - 1) shift' root' tl', lastElem)
  where
    lastElem = tl ! (arrayLength tl - 1)
    newLast = size - 2

    -- Remove the right-most leaf, copying one path. 'Nothing' means the
    -- node became empty and should be removed from its parent too.
    popTail level (Branch children)
      | level > bits = case popTail (level - bits) (children ! i) of
          Nothing
            | i == 0 -> Nothing
            | otherwise -> Just (Branch (arrayTake i children))
          Just child -> Just (Branch (arraySet i child children))
      | i == 0 = Nothing
      | otherwise = Just (Branch (arrayTake i children))
      where
        i = slot level newLast
    popTail _ (Leaf _) = Nothing -- unreachable: leaves sit at level 0

    -- A root with a single child is redundant; drop a level.
    collapse s (Branch children)
      | s > bits && arrayLength children == 1 = (s - bits, children ! 0)
    collapse s node = (s, node)

-- | The leaf array holding tree index @i@ (which must be in the tree).
leafContaining :: Int -> Node a -> Int -> Array Int a
leafContaining _ (Leaf a) _ = a
leafContaining level (Branch children) i =
  leafContaining (level - bits) (children ! slot level i) i

-- | Element at an index, if in range. O(log32 n).
lookup :: Int -> Vector a -> Maybe a
lookup i (Vector size shift root tl)
  | i < 0 || i >= size = Nothing
  | i >= tailOffset size = Just (tl ! (i - tailOffset size))
  | otherwise = Just (leafContaining shift root i ! (i .&. mask))

-- | Apply a function at an index, copying only the root-to-leaf path.
-- Out-of-range indices return the vector unchanged. O(log32 n).
adjust :: (a -> a) -> Int -> Vector a -> Vector a
adjust f i v@(Vector size shift root tl)
  | i < 0 || i >= size = v
  | i >= off = v {vTail = modify (i - off) tl}
  | otherwise = v {vRoot = go shift root}
  where
    off = tailOffset size
    modify j a = a // [(j, f (a ! j))]
    go _ (Leaf a) = Leaf (modify (i .&. mask) a)
    go level (Branch children) =
      let j = slot level i
       in Branch (children // [(j, go (level - bits) (children ! j))])

------------------------------------------------------------------------------
-- Invariants

-- | Every structural invariant the algorithms rely on that this vector
-- breaks, as human-readable messages. Empty means the vector is well formed.
-- Used by the property tests after every operation.
invariantViolations :: Vector a -> [String]
invariantViolations (Vector size shift root tl) =
  concat
    [ check (size >= 0) "negative size"
    , check (shift >= bits && shift `mod` bits == 0) ("bad shift " ++ show shift)
    , check (arrayLength tl == size - off) "tail length /= size - tailOffset"
    , check (size == 0 || arrayLength tl >= 1) "non-empty vector with empty tail"
    , check (arrayLength tl <= width) "tail longer than width"
    , check (treeCount == off) ("tree holds " ++ show treeCount ++ ", expected " ++ show off)
    , check (shift == bits || rootChildren >= 2) "root has a single child above minimum depth"
    , nodeViolations shift root
    ]
  where
    off = tailOffset size
    treeCount = length root
    rootChildren = case root of
      Branch children -> arrayLength children
      Leaf _ -> 0
    check ok msg = [msg | not ok]

    nodeViolations 0 (Leaf a) = check (arrayLength a == width) "partial leaf in tree"
    nodeViolations 0 (Branch _) = ["branch at leaf level"]
    nodeViolations _ (Leaf _) = ["leaf above leaf level"]
    nodeViolations level (Branch children) =
      check (arrayLength children <= width) "branch wider than width"
        ++ concatMap (nodeViolations (level - bits)) (elems children)
