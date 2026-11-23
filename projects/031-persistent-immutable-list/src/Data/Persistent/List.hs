{-# LANGUAGE DeriveTraversable #-}

-- |
-- Module      : Data.Persistent.List
-- Description : A persistent singly linked list with structural sharing.
--
-- The classic functional data structure. Every operation returns a /new/
-- list and leaves its inputs untouched, yet almost nothing is copied:
--
-- * 'cons' allocates exactly one cell and shares the whole input as its tail.
-- * 'drop' and 'tail' allocate nothing at all; the result /is/ a suffix of
--   the input.
-- * 'update', 'adjust', 'take' and 'append' copy only the prefix they must
--   change and share everything after it.
--
-- The spine is strict (each cell's tail is evaluated when the cell is), so
-- lists are always finite and 'length' never forces a thunk chain. Elements
-- stay lazy.
--
-- Import qualified, since several names clash with the Prelude:
--
-- > import qualified Data.Persistent.List as L
module Data.Persistent.List
  ( -- * Type
    List (..)

    -- * Construction
  , empty
  , singleton
  , cons
  , fromList

    -- * Deconstruction
  , uncons
  , head
  , tail

    -- * Indexing
  , (!?)
  , update
  , adjust

    -- * Slicing
  , take
  , drop
  , splitAt

    -- * Transformations
  , append
  , reverse
  , filter
  ) where

import qualified Data.Foldable as F
import Data.Maybe (fromMaybe)
import Prelude hiding (drop, filter, head, reverse, splitAt, tail, take)

-- | A finite, immutable singly linked list.
data List a
  = Nil
  | Cons a !(List a)
  deriving (Functor, Foldable, Traversable)

-- Equality and ordering are the list ones; deriving would give the same
-- answers but the explicit versions document the intent.
instance Eq a => Eq (List a) where
  xs == ys = F.toList xs == F.toList ys

instance Ord a => Ord (List a) where
  compare xs ys = compare (F.toList xs) (F.toList ys)

-- | Shows as @fromList [..]@ so the output is valid Haskell.
instance Show a => Show (List a) where
  showsPrec d xs =
    showParen (d > 10) $ showString "fromList " . shows (F.toList xs)

-- | Concatenation. Copies the left operand and shares the right one.
instance Semigroup (List a) where
  (<>) = append

instance Monoid (List a) where
  mempty = Nil

-- | The empty list. O(1).
empty :: List a
empty = Nil

-- | A one-element list. O(1).
singleton :: a -> List a
singleton x = Cons x Nil

-- | Prepend an element, sharing the entire input list. O(1).
cons :: a -> List a -> List a
cons = Cons

-- | Build from a Haskell list. O(n). The input must be finite.
fromList :: [a] -> List a
fromList = foldr Cons Nil

-- | Split into first element and remainder. The remainder is shared. O(1).
uncons :: List a -> Maybe (a, List a)
uncons Nil = Nothing
uncons (Cons x xs) = Just (x, xs)

-- | First element, if any. O(1).
head :: List a -> Maybe a
head = fmap fst . uncons

-- | Everything but the first element, if non-empty. Allocates nothing. O(1).
tail :: List a -> Maybe (List a)
tail = fmap snd . uncons

-- | Safe indexing. O(i).
(!?) :: List a -> Int -> Maybe a
xs !? i
  | i < 0 = Nothing
  | otherwise = go i xs
  where
    go _ Nil = Nothing
    go 0 (Cons y _) = Just y
    go n (Cons _ ys) = go (n - 1) ys

infixl 9 !?

-- | Replace the element at an index. Out-of-range indices return the list
-- unchanged. Copies the @i@ cells before the index and shares the suffix
-- after it. O(i).
update :: Int -> a -> List a -> List a
update i x = adjust (const x) i

-- | Apply a function to the element at an index. Same sharing and
-- out-of-range behaviour as 'update'. O(i).
adjust :: (a -> a) -> Int -> List a -> List a
adjust f i xs
  | i < 0 = xs
  | otherwise = fromMaybe xs (go i xs)
  where
    -- 'Nothing' signals "index out of range", so a failed update returns
    -- the original list instead of rebuilding an identical copy.
    go _ Nil = Nothing
    go 0 (Cons y ys) = Just (Cons (f y) ys)
    go n (Cons y ys) = Cons y <$> go (n - 1) ys

-- | The first @n@ elements. Copies them; returns the input itself when it
-- is already short enough. O(min n len).
take :: Int -> List a -> List a
take n xs = fst (splitAt n xs)

-- | Drop the first @n@ elements. Allocates nothing: the result is a suffix
-- of the input. O(min n len).
drop :: Int -> List a -> List a
drop n xs
  | n <= 0 = xs
  | otherwise = case xs of
      Nil -> Nil
      Cons _ ys -> drop (n - 1) ys

-- | @splitAt n xs == (take n xs, drop n xs)@ in a single pass. The second
-- component is shared with the input.
splitAt :: Int -> List a -> (List a, List a)
splitAt n xs
  | n <= 0 = (Nil, xs)
  | otherwise = case xs of
      Nil -> (Nil, Nil)
      Cons y ys -> let (front, back) = splitAt (n - 1) ys in (Cons y front, back)

-- | Concatenate. Copies @xs@, shares @ys@. O(length xs).
append :: List a -> List a -> List a
append Nil ys = ys
append xs Nil = xs
append (Cons x xs) ys = Cons x (append xs ys)

-- | Reverse with an accumulator. O(n); necessarily copies every cell.
reverse :: List a -> List a
reverse = F.foldl' (flip Cons) Nil

-- | Keep the elements satisfying a predicate. The longest suffix in which
-- every element passes is shared rather than copied.
filter :: (a -> Bool) -> List a -> List a
filter p xs = fromMaybe xs (go xs)
  where
    -- 'Nothing' means "this suffix is unchanged, reuse it".
    go Nil = Nothing
    go (Cons y ys) = case go ys of
      Nothing
        | p y -> Nothing
        | otherwise -> Just ys
      Just ys'
        | p y -> Just (Cons y ys')
        | otherwise -> Just ys'
