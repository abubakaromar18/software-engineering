-- | A dependency-free micro-benchmark comparing the persistent vector with
-- Data.Sequence (a finger tree) and the cons list. It reports the median
-- of a few wall-clock runs, so treat the numbers as relative, not absolute.
--
-- Each workload is a pure function of the input size; the bench is
-- compiled with -fno-full-laziness so GHC cannot float out and share one
-- result between runs.
module Main (main) where

import Control.Exception (evaluate)
import Data.List (sort)
import qualified Data.Foldable as F
import qualified Data.Persistent.List as L
import qualified Data.Persistent.Vector as V
import qualified Data.Sequence as S
import GHC.Clock (getMonotonicTime)
import Text.Printf (printf)

-- | Pseudo-random but deterministic indices below @size@.
indices :: Int -> Int -> [Int]
indices size count = [i * 7919 `mod` size | i <- [1 .. count]]

-- | Warm up once, then report the median of five runs of @work size@.
timed :: Int -> String -> (Int -> Int) -> IO ()
timed size label work = do
  _ <- evaluate (work size)
  samples <- mapM (const sample) [1 .. 5 :: Int]
  printf "%-32s %9.1f ms\n" label (sort samples !! 2 * 1000)
  where
    sample = do
      start <- getMonotonicTime
      _ <- evaluate (work size)
      end <- getMonotonicTime
      pure (end - start :: Double)

main :: IO ()
main = do
  let n = 200000
      fewer = 200 -- the list is O(i) per access; keep its run short
  printf "n = %d\n\n" n
  vec <- evaluate (V.fromList [1 .. n])
  sq <- evaluate (S.fromList [1 .. n])
  lst <- evaluate (L.fromList [1 .. n])

  timed n "Vector  fromList (bulk)" (\k -> V.length (V.fromList [1 .. k]))
  timed n "Vector  repeated snoc" (\k -> V.length (F.foldl' V.snoc V.empty [1 .. k]))
  timed n "Seq     fromList" (\k -> S.length (S.fromList [1 .. k]))
  timed n "List    fromList" (\k -> length (L.fromList [1 .. k]))
  putStrLn ""
  timed n "Vector  lookup x n" (\k -> sum [maybe 0 id (vec V.!? i) | i <- indices k k])
  timed n "Seq     lookup x n" (\k -> sum [maybe 0 id (S.lookup i sq) | i <- indices k k])
  timed n "List    lookup x 200" (\k -> sum [maybe 0 id (lst L.!? i) | i <- indices k fewer])
  putStrLn ""
  timed n "Vector  update x n" (\k -> maybe 0 id (F.foldl' (\v i -> V.update i 0 v) vec (indices k k) V.!? 0))
  timed n "Seq     update x n" (\k -> maybe 0 id (S.lookup 0 (F.foldl' (\s i -> S.update i 0 s) sq (indices k k))))
  timed n "List    update x 200" (\k -> maybe 0 id (L.head (F.foldl' (\l i -> L.update i 0 l) lst (indices k fewer))))
