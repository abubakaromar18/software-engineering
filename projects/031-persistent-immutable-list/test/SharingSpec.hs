-- | Structural sharing is the point of these data structures, so we test it
-- directly: 'StableName' equality proves two values are the /same heap
-- object/, not merely equal. (A 'StableName' check can produce false
-- negatives in principle, never false positives, so passing tests are
-- meaningful.)
module SharingSpec (spec) where

import Control.Exception (evaluate)
import Data.Array (elems)
import qualified Data.Persistent.List as L
import qualified Data.Persistent.Vector as V
import Data.Persistent.Vector.Internal (Node (..), Vector (..))
import System.Mem.StableName (makeStableName)
import Test.Hspec

-- | Are the two (evaluated) values the same object in memory?
sameObject :: a -> a -> IO Bool
sameObject x y = do
  x' <- evaluate x
  y' <- evaluate y
  (==) <$> makeStableName x' <*> makeStableName y'

shouldShare :: a -> a -> Expectation
shouldShare x y = sameObject x y >>= (`shouldBe` True)

shouldNotShare :: a -> a -> Expectation
shouldNotShare x y = sameObject x y >>= (`shouldBe` False)

rootChildren :: Vector a -> [Node a]
rootChildren v = case vRoot v of
  Branch cs -> elems cs
  Leaf _ -> []

spec :: Spec
spec = describe "structural sharing" $ do
  describe "List" $ do
    let xs = L.fromList [1 .. 100 :: Int]
    it "cons shares the whole input as its tail" $
      maybe (expectationFailure "empty") (`shouldShare` xs) (L.tail (L.cons 0 xs))
    it "drop allocates nothing: the result is a suffix of the input" $
      L.drop 40 xs `shouldShare` L.drop 40 xs
    it "update copies the prefix and shares the suffix" $ do
      let ys = L.update 10 0 xs
      L.drop 11 ys `shouldShare` L.drop 11 xs
      L.drop 10 ys `shouldNotShare` L.drop 10 xs
    it "an out-of-range update returns the input itself" $
      L.update 500 0 xs `shouldShare` xs
    it "append shares its right operand" $ do
      let front = L.fromList [1 .. 5 :: Int]
      L.drop 5 (front <> xs) `shouldShare` xs
    it "filter shares the longest unchanged suffix" $ do
      let zs = L.fromList ([1, 2, 3] ++ replicate 50 (2 :: Int))
      -- [1,2,3,2,2..] filters to 2 : <the original suffix from index 3>
      L.drop 1 (L.filter even zs) `shouldShare` L.drop 3 zs

  describe "Vector" $ do
    let v = V.fromList [1 .. 5000 :: Int] -- depth 2: root -> 5 branches -> leaves
    it "snoc into a non-full tail shares the entire tree" $
      vRoot (V.snoc v 0) `shouldShare` vRoot v
    it "updating the tail shares the entire tree" $
      -- 5000 elements: the tail holds indices 4992..4999.
      vRoot (V.update 4995 0 v) `shouldShare` vRoot v
    it "updating inside the tree copies one path and shares every other subtree" $ do
      let v' = V.update 1500 0 v -- lives under root child 1500 >> 10 = 1
          pairs = zip (rootChildren v) (rootChildren v')
      length pairs `shouldBe` 5
      mapM_ (\(i, (a, b)) -> if i == (1 :: Int) then a `shouldNotShare` b else a `shouldShare` b) (zip [0 ..] pairs)
      vTail v' `shouldShare` vTail v
    it "an out-of-range update returns the input itself" $
      V.update 99999 0 v `shouldShare` v
