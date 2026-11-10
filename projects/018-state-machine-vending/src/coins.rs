//! A bag of coins with finite counts per denomination, plus change-making.
//!
//! Real machines hold a limited number of each coin, so "always give the
//! largest coin first" (greedy) is not enough: with three dimes and no
//! nickels, greedy cannot make 30¢ out of a quarter-first strategy even
//! though 3 × 10¢ works. [`CoinBag::make_change`] therefore solves the
//! *bounded* change-making problem exactly with dynamic programming.

use crate::money::{Cents, Coin};
use std::fmt;

/// Counts of each coin, indexed by [`Coin::index`].
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CoinBag {
    counts: [u32; Coin::ALL.len()],
}

impl CoinBag {
    pub fn new() -> Self {
        Self::default()
    }

    /// Builds a bag from `(coin, count)` pairs; repeated coins accumulate.
    pub fn from_counts(pairs: &[(Coin, u32)]) -> Self {
        let mut bag = Self::new();
        for &(coin, count) in pairs {
            bag.add_many(coin, count);
        }
        bag
    }

    pub fn add(&mut self, coin: Coin) {
        self.add_many(coin, 1);
    }

    pub fn add_many(&mut self, coin: Coin, count: u32) {
        self.counts[coin.index()] += count;
    }

    /// Moves every coin out of `other` into `self`.
    pub fn absorb(&mut self, other: CoinBag) {
        for coin in Coin::ALL {
            self.add_many(coin, other.count(coin));
        }
    }

    pub fn count(&self, coin: Coin) -> u32 {
        self.counts[coin.index()]
    }

    pub fn total(&self) -> Cents {
        Coin::ALL
            .iter()
            .map(|&c| Cents(c.value().0 * self.count(c)))
            .fold(Cents::ZERO, |a, b| a + b)
    }

    pub fn coin_count(&self) -> u32 {
        self.counts.iter().sum()
    }

    pub fn is_empty(&self) -> bool {
        self.coin_count() == 0
    }

    /// Removes `amount` from the bag using the fewest coins possible and
    /// returns those coins, or `None` (leaving the bag untouched) if the
    /// amount cannot be made from what is in the bag.
    pub fn make_change(&mut self, amount: Cents) -> Option<CoinBag> {
        let change = self.plan_change(amount)?;
        for coin in Coin::ALL {
            self.counts[coin.index()] -= change.count(coin);
        }
        Some(change)
    }

    /// Like [`make_change`](Self::make_change) but only reports whether it
    /// is possible, without removing anything.
    pub fn can_make_change(&self, amount: Cents) -> bool {
        self.plan_change(amount).is_some()
    }

    /// Bounded change-making via 0/1 knapsack over individual coins.
    ///
    /// `best[a]` holds the cheapest known way (fewest coins) to pay exactly
    /// `a` cents. Each physical coin is considered once, iterating amounts
    /// downwards so a coin is never reused. Complexity is
    /// O(usable coins × amount), which is tiny for vending-machine sums.
    fn plan_change(&self, amount: Cents) -> Option<CoinBag> {
        let target = amount.0 as usize;
        let mut best: Vec<Option<CoinBag>> = vec![None; target + 1];
        best[0] = Some(CoinBag::new());

        for coin in Coin::ALL {
            let value = coin.value().0 as usize;
            // Coins beyond target / value can never all be used.
            let usable = (self.count(coin) as usize).min(target / value);
            for _ in 0..usable {
                for a in (value..=target).rev() {
                    let Some(prev) = &best[a - value] else {
                        continue;
                    };
                    let candidate_len = prev.coin_count() + 1;
                    let better = best[a]
                        .as_ref()
                        .map_or(true, |cur| candidate_len < cur.coin_count());
                    if better {
                        let mut next = prev.clone();
                        next.add(coin);
                        best[a] = Some(next);
                    }
                }
            }
        }
        best.swap_remove(target)
    }
}

impl fmt::Display for CoinBag {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.is_empty() {
            return f.write_str("no coins");
        }
        let parts: Vec<String> = Coin::ALL
            .iter()
            .filter(|&&c| self.count(c) > 0)
            .map(|&c| format!("{}×{}", self.count(c), c))
            .collect();
        write!(f, "{} ({})", parts.join(", "), self.total())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn totals_and_counts() {
        let bag = CoinBag::from_counts(&[(Coin::Quarter, 3), (Coin::Dime, 2)]);
        assert_eq!(bag.total(), Cents(95));
        assert_eq!(bag.coin_count(), 5);
    }

    #[test]
    fn zero_change_is_always_possible() {
        let mut bag = CoinBag::new();
        assert_eq!(bag.make_change(Cents::ZERO), Some(CoinBag::new()));
    }

    #[test]
    fn uses_fewest_coins() {
        let mut bag =
            CoinBag::from_counts(&[(Coin::Quarter, 4), (Coin::Dime, 5), (Coin::Nickel, 5)]);
        let change = bag.make_change(Cents(40)).unwrap();
        assert_eq!(
            change,
            CoinBag::from_counts(&[(Coin::Quarter, 1), (Coin::Dime, 1), (Coin::Nickel, 1)])
        );
        assert_eq!(bag.total(), Cents(100 + 50 + 25 - 40));
    }

    #[test]
    fn succeeds_where_greedy_fails() {
        // Greedy takes the quarter first and is left needing 5¢ with no
        // nickels. The exact solver finds 3 dimes instead.
        let mut bag = CoinBag::from_counts(&[(Coin::Quarter, 1), (Coin::Dime, 3)]);
        let change = bag.make_change(Cents(30)).unwrap();
        assert_eq!(change, CoinBag::from_counts(&[(Coin::Dime, 3)]));
        assert_eq!(bag, CoinBag::from_counts(&[(Coin::Quarter, 1)]));
    }

    #[test]
    fn impossible_change_leaves_bag_untouched() {
        let mut bag = CoinBag::from_counts(&[(Coin::Quarter, 2)]);
        let before = bag.clone();
        assert_eq!(bag.make_change(Cents(15)), None);
        assert_eq!(bag, before);
        assert!(!bag.can_make_change(Cents(15)));
    }

    #[test]
    fn respects_finite_counts() {
        let bag = CoinBag::from_counts(&[(Coin::Dime, 2)]);
        assert!(bag.can_make_change(Cents(20)));
        assert!(!bag.can_make_change(Cents(30)));
    }

    #[test]
    fn display_lists_nonzero_coins() {
        let bag = CoinBag::from_counts(&[(Coin::Dollar, 1), (Coin::Nickel, 2)]);
        assert_eq!(bag.to_string(), "1×dollar, 2×nickel ($1.10)");
        assert_eq!(CoinBag::new().to_string(), "no coins");
    }
}
