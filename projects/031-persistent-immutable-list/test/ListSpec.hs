module ListSpec (spec) where

import qualified Data.Foldable as F
import qualified Data.List as DL
import qualified Data.Persistent.List as L
import Gen (genSizedList)
import Test.Hspec
import Test.Hspec.QuickCheck (prop)
import Test.QuickCheck

-- | Haskell's built-in list is the reference model for every operation.
instance Arbitrary a => Arbitrary (L.List a) where
  arbitrary = L.fromList <$> arbitrary
  shrink = map L.fromList . shrink . F.toList

-- | Index of an element in a list, plus some out-of-range values.
anyIndex :: [a] -> Gen Int
anyIndex xs = choose (-2, length xs + 2)

spec :: Spec
spec = describe "Data.Persistent.List" $ do
  describe "agrees with Prelude lists" $ do
    prop "fromList / toList round-trip" $
      forAll genSizedList $ \xs -> F.toList (L.fromList xs) === (xs :: [Int])
    prop "cons" $ \x xs -> F.toList (L.cons x xs) === x : F.toList (xs :: L.List Int)
    prop "uncons" $ \xs ->
      fmap (fmap F.toList) (L.uncons xs) === DL.uncons (F.toList (xs :: L.List Int))
    prop "head / tail" $ \xs -> do
      let ys = F.toList (xs :: L.List Int)
      L.head xs === fmap fst (DL.uncons ys)
        .&&. fmap F.toList (L.tail xs) === fmap snd (DL.uncons ys)
    prop "length" $ \xs -> length xs === length (F.toList (xs :: L.List Int))
    prop "(!?)" $ \xs -> forAll (anyIndex (F.toList xs)) $ \i ->
      xs L.!? i === lookup i (zip [0 ..] (F.toList (xs :: L.List Int)))
    prop "update" $ \xs x -> forAll (anyIndex (F.toList xs)) $ \i ->
      F.toList (L.update i x xs) === modelUpdate i (const x) (F.toList (xs :: L.List Int))
    prop "adjust" $ \xs -> forAll (anyIndex (F.toList xs)) $ \i ->
      F.toList (L.adjust negate i xs) === modelUpdate i negate (F.toList (xs :: L.List Int))
    prop "take / drop / splitAt" $ \xs (Small n) -> do
      let ys = F.toList (xs :: L.List Int)
      F.toList (L.take n xs) === take n ys
        .&&. F.toList (L.drop n xs) === drop n ys
        .&&. (\(a, b) -> (F.toList a, F.toList b)) (L.splitAt n xs) === splitAt n ys
    prop "append" $ \xs ys ->
      F.toList (L.append xs ys) === F.toList xs ++ F.toList (ys :: L.List Int)
    prop "reverse" $ \xs -> F.toList (L.reverse xs) === reverse (F.toList (xs :: L.List Int))
    prop "filter" $ \xs -> F.toList (L.filter even xs) === filter even (F.toList (xs :: L.List Int))
    prop "Eq and Ord match the list instances" $ \xs ys ->
      (xs == ys) === (F.toList xs == F.toList (ys :: L.List Int))
        .&&. compare xs ys === compare (F.toList xs) (F.toList ys)

  describe "laws" $ do
    prop "reverse is an involution" $ \xs -> L.reverse (L.reverse xs) === (xs :: L.List Int)
    prop "reverse distributes over append, flipped" $ \xs ys ->
      L.reverse (xs <> ys) === L.reverse ys <> L.reverse (xs :: L.List Int)
    prop "semigroup associativity" $ \a b c -> (a <> b) <> c === a <> (b <> (c :: L.List Int))
    prop "monoid identity" $ \a -> (mempty <> a === (a :: L.List Int)) .&&. (a <> mempty === a)
    prop "functor identity" $ \xs -> fmap id xs === (xs :: L.List Int)
    prop "functor composition" functorComposition
    prop "traverse with Maybe matches lists" $ \xs ->
      let f x = if x > 100 then Nothing else Just (x * 2)
       in fmap F.toList (traverse f xs) === traverse f (F.toList (xs :: L.List Int))
    prop "splitAt then append restores the list" $ \xs n ->
      uncurry (<>) (L.splitAt n xs) === (xs :: L.List Int)
    prop "update then lookup reads the new value" $ \xs x -> not (null xs) ==>
      forAll (choose (0, length xs - 1)) $ \i -> L.update i x xs L.!? i === Just (x :: Int)

  describe "persistence" $
    prop "operations never change their input" $ \xs x -> do
      let original = F.toList (xs :: L.List Int)
          derived = [L.cons x xs, L.update 0 x xs, L.reverse xs, L.drop 1 xs, xs <> xs]
      -- Force every derived version, then check the original still reads back.
      sum (map length derived) `seq` F.toList xs === original

  describe "Show" $
    it "renders as a fromList expression" $
      show (L.fromList [1, 2, 3 :: Int]) `shouldBe` "fromList [1,2,3]"

-- | Reference implementation of index update on Prelude lists.
modelUpdate :: Int -> (a -> a) -> [a] -> [a]
modelUpdate i f xs = [if j == i then f y else y | (j, y) <- zip [0 ..] xs]

functorComposition :: Fun Int Int -> Fun Int Int -> L.List Int -> Property
functorComposition (Fn f) (Fn g) xs = fmap (f . g) xs === (fmap f . fmap g) xs
