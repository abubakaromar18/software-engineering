-- | Generators shared by the specs.
module Gen
  ( genSizedList
  , genBoundarySize
  , boundarySizes
  , Op (..)
  , genOps
  ) where

import Test.QuickCheck

-- | Sizes at which the vector's shape changes: the tail fills, the first
-- leaf enters the tree, the root overflows from one to two and from two to
-- three levels of branches. Bugs in tries live at these edges.
boundarySizes :: [Int]
boundarySizes =
  [0, 1, 2, 31, 32, 33, 63, 64, 65, 1023, 1024, 1025, 1055, 1056, 1057, 1088, 1089, 32799, 32800, 32801, 32833]

-- | Mostly small sizes, often near a boundary, occasionally large.
genBoundarySize :: Gen Int
genBoundarySize =
  frequency
    [ (5, choose (0, 100))
    , (4, do b <- elements (takeWhile (< 2000) boundarySizes); d <- choose (-2, 2); pure (max 0 (b + d)))
    , (1, choose (1000, 5000))
    ]

-- | A list whose length is drawn from 'genBoundarySize'.
genSizedList :: Arbitrary a => Gen [a]
genSizedList = genBoundarySize >>= flip vectorOf arbitrary

-- | Operations for the model-based (state machine) test.
data Op
  = Snoc Int
  | Unsnoc
  | Update Int Int
  | Increment Int
  deriving (Show)

-- | A sequence of operations. Snoc and Unsnoc are weighted to make the size
-- wander back and forth across boundaries; indices may be out of range on
-- purpose.
genOps :: Gen [Op]
genOps = listOf1 genOp
  where
    genOp =
      frequency
        [ (4, Snoc <$> arbitrary)
        , (4, pure Unsnoc)
        , (2, Update <$> genIndex <*> arbitrary)
        , (1, Increment <$> genIndex)
        ]
    genIndex = oneof [choose (-2, 40), choose (0, 2000), choose (0, 40000)]
