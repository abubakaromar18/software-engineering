module Main (main) where

import qualified ListSpec
import qualified SharingSpec
import qualified VectorSpec
import Test.Hspec

main :: IO ()
main = hspec $ do
  ListSpec.spec
  VectorSpec.spec
  SharingSpec.spec
