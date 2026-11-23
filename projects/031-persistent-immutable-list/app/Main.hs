-- | A short tour of persistence: every "modification" below produces a new
-- version while the old ones stay valid and unchanged.
module Main (main) where

import qualified Data.Foldable as F
import qualified Data.Persistent.List as L
import qualified Data.Persistent.Vector as V
import qualified Data.Persistent.Vector.Internal as I

main :: IO ()
main = do
  section "Persistent list"
  let xs = L.fromList [1 .. 5 :: Int]
      ys = L.cons 0 xs -- shares all of xs
      zs = L.update 2 99 xs -- copies 3 cells, shares the last 2
  putStrLn ("xs                = " ++ show xs)
  putStrLn ("cons 0 xs         = " ++ show ys)
  putStrLn ("update 2 99 xs    = " ++ show zs)
  putStrLn ("xs afterwards     = " ++ show xs)

  section "Persistent vector: versions"
  let v1 = V.fromList "persistent"
      v2 = V.update 0 'P' v1
      v3 = v2 V.|> '!'
      v4 = maybe V.empty fst (V.unsnoc v1)
  mapM_
    (\(name, v) -> putStrLn (name ++ " = " ++ F.toList v))
    [("v1 (original)     ", v1), ("v2 = update 0 'P' ", v2), ("v3 = v2 |> '!'    ", v3), ("v4 = init v1      ", v4)]

  section "Persistent vector: shape as it grows"
  putStrLn "     size  depth     tree  tail"
  mapM_ (putStrLn . shapeRow) [0, 1, 32, 33, 1056, 1057, 32800, 32801, 1000000]

  section "Persistent vector: a thousand versions are cheap"
  let base = V.fromList [0 .. 999999 :: Int]
      versions = scanl (\v i -> V.update (i * 7919 `mod` 1000000) (-i) v) base [1 .. 1000]
  putStrLn ("built " ++ show (length versions) ++ " versions of a 1,000,000-element vector")
  putStrLn ("original element 7919  = " ++ show (base V.!? 7919))
  putStrLn ("latest   element 7919  = " ++ show (last versions V.!? 7919))
  putStrLn "each update copied 4 small arrays (depth 3 + leaf), not 1,000,000 slots"
  where
    section title = putStrLn ("\n== " ++ title ++ " ==")
    shapeRow n =
      let v = V.fromList [1 .. n :: Int]
          off = I.tailOffset n
       in pad 9 (show n) ++ pad 7 (show (I.depth v)) ++ pad 9 (show off) ++ pad 6 (show (n - off))
    pad k s = replicate (k - length s) ' ' ++ s
