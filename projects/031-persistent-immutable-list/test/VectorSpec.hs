module VectorSpec (spec) where

import Control.Monad (foldM)
import qualified Data.Foldable as F
import qualified Data.Persistent.Vector as V
import Data.Persistent.Vector.Internal (invariantViolations)
import qualified Data.Persistent.Vector.Internal as I
import Gen
import Test.Hspec
import Test.Hspec.QuickCheck (modifyMaxSuccess, prop)
import Test.QuickCheck

instance Arbitrary a => Arbitrary (V.Vector a) where
  arbitrary = V.fromList <$> genSizedList
  shrink = map V.fromList . shrink . F.toList

-- | A vector is well formed when it has no invariant violations.
wellFormed :: V.Vector a -> Property
wellFormed v = counterexample (unlines (invariantViolations v)) (null (invariantViolations v))

-- | Pops every element, checking contents at every size. The O(n)
-- invariant check runs at every step for small vectors, and only at the
-- shape-changing sizes for large ones, to keep the test fast. The model is
-- given newest-element-first so each step is O(1). Returns the first
-- failure, so a long drain stays a cheap loop rather than a deep chain of
-- QuickCheck conjunctions.
drainChecked :: V.Vector Int -> [Int] -> Either String ()
drainChecked v0 = go v0
  where
    thorough = V.length v0 <= 2000
    go v model = case (V.unsnoc v, model) of
      (Nothing, []) -> Right ()
      (Just (v', x), y : rest)
        | x /= y -> Left ("popped " ++ show x ++ ", expected " ++ show y)
        | V.length v' /= length rest -> Left ("wrong length at " ++ show (V.length v'))
        | (thorough || V.length v' `elem` boundarySizes) && not (null (invariantViolations v')) ->
            Left ("size " ++ show (V.length v') ++ ": " ++ unwords (invariantViolations v'))
        | otherwise -> go v' rest
      _ -> Left "unsnoc disagrees with model about emptiness"

spec :: Spec
spec = describe "Data.Persistent.Vector" $ do
  describe "agrees with Prelude lists" $ do
    prop "fromList / toList round-trip and is well formed" $
      forAll genSizedList $ \xs -> let v = V.fromList (xs :: [Int]) in F.toList v === xs .&&. wellFormed v
    prop "length / null" $ \v ->
      V.length v === length (F.toList (v :: V.Vector Int)) .&&. V.null v === null (F.toList v)
    prop "lookup at every index, and out of range" $ \v -> do
      let xs = F.toList (v :: V.Vector Int)
          n = length xs
      conjoin [v V.!? i === lookup i (zip [0 ..] xs) | i <- [-1 .. n]]
    prop "last" $ \v -> V.last v === (if null v then Nothing else Just (last (F.toList (v :: V.Vector Int))))
    prop "update" $ \v x -> forAll (choose (-2, V.length v + 2)) $ \i -> do
      let v' = V.update i x (v :: V.Vector Int)
      F.toList v' === [if j == i then x else y | (j, y) <- zip [0 ..] (F.toList v)] .&&. wellFormed v'
    prop "fmap / foldr / foldl' match lists" $ \v -> do
      let xs = F.toList (v :: V.Vector Int)
      F.toList (fmap (* 3) v) === map (* 3) xs
        .&&. foldr (:) [] v === xs
        .&&. F.foldl' (flip (:)) [] v === reverse xs
    prop "traverse with Maybe matches lists" $ \v ->
      let f x = if x > 100 then Nothing else Just (x + 1)
       in fmap F.toList (traverse f v) === traverse f (F.toList (v :: V.Vector Int))
    prop "Eq and Ord match the list instances" $ \v w ->
      (v == w) === (F.toList v == F.toList (w :: V.Vector Int))
        .&&. compare v w === compare (F.toList v) (F.toList w)
    prop "(<>) is concatenation" $ \v w ->
      F.toList (v <> w) === F.toList v ++ F.toList (w :: V.Vector Int) .&&. wellFormed (v <> w)

  describe "laws" $ do
    prop "semigroup associativity" $ \a b c -> (a <> b) <> c === a <> (b <> (c :: V.Vector Int))
    prop "monoid identity" $ \a -> (mempty <> a === (a :: V.Vector Int)) .&&. (a <> mempty === a)
    prop "functor identity" $ \v -> fmap id v === (v :: V.Vector Int)
    prop "unsnoc . snoc == Just" $ \v x ->
      fmap (\(w, y) -> (F.toList w, y)) (V.unsnoc (V.snoc v x)) === Just (F.toList (v :: V.Vector Int), x)
    prop "update i (lookup i) is identity" $ \v -> not (V.null v) ==>
      forAll (choose (0, V.length v - 1)) $ \i ->
        maybe (property False) (\x -> V.update i x v === (v :: V.Vector Int)) (V.lookup i v)

  describe "shape at boundary sizes" $
    -- Deterministic, so each size is checked once rather than sampled.
    mapM_
      ( \n -> it ("size " ++ show n ++ ": bulk and incremental builds agree; read back; drain") $ once $ do
          let xs = [1 .. n]
              v = V.fromList xs
              snocced = F.foldl' V.snoc V.empty xs -- the incremental path
          wellFormed v
            .&&. wellFormed snocced
            .&&. I.depth snocced === I.depth v
            .&&. F.toList snocced === xs
            .&&. F.toList v === xs
            .&&. conjoin [V.lookup i v === Just (i + 1) | i <- [0, n `div` 2, n - 1], n > 0]
            .&&. either (`counterexample` False) (const (property True)) (drainChecked v (reverse xs))
      )
      boundarySizes

  describe "depth" $
    it "grows one level per factor of 32" $ do
      let depthAt n = I.depth (V.fromList [1 .. n :: Int])
      map depthAt [0, 1056, 1057, 32800, 32801] `shouldBe` [1, 1, 2, 2, 3]

  describe "model-based state machine" $
    modifyMaxSuccess (const 200) $
      prop "random op sequences match a list model, and every old version survives" $
        forAll (elements [0, 30, 1050, 32795]) $ \start ->
          forAll genOps $ \ops -> do
            let initial = (V.fromList [1 .. start], [1 .. start])
            case foldM step [initial] ops of
              Left err -> counterexample err False
              Right history ->
                -- Every version ever produced still holds exactly its model.
                conjoin [F.toList v === m | (v, m) <- history]

  describe "Show" $
    it "renders as a fromList expression" $
      show (V.fromList "abc") `shouldBe` "fromList \"abc\""

-- | Apply one op to the newest version, validate it, and record it.
step :: [(V.Vector Int, [Int])] -> Op -> Either String [(V.Vector Int, [Int])]
step [] _ = Left "empty history"
step history@((v, m) : _) op = do
  let (v', m') = apply op
      bad = invariantViolations v'
  if not (null bad)
    then Left (show op ++ " broke invariants: " ++ unwords bad)
    else
      if V.length v' /= length m' || V.last v' /= lastMaybe m'
        then Left (show op ++ " diverged from model")
        else Right ((v', m') : history)
  where
    apply (Snoc x) = (V.snoc v x, m ++ [x])
    apply Unsnoc = maybe (v, m) (\(w, _) -> (w, init m)) (V.unsnoc v)
    apply (Update i x) = (V.update i x v, modelSet i (const x) m)
    apply (Increment i) = (V.adjust (+ 1) i v, modelSet i (+ 1) m)
    modelSet i f = zipWith (\j y -> if j == i then f y else y) [0 ..]
    lastMaybe [] = Nothing
    lastMaybe xs = Just (last xs)
