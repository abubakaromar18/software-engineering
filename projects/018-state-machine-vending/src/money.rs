//! Money and coins.
//!
//! All amounts are integer cents so that arithmetic is exact. `Cents` is a
//! newtype rather than a bare `u32` so a price can never be confused with a
//! slot number or a coin count.

use std::fmt;
use std::ops::{Add, AddAssign};

/// An amount of money in US cents.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct Cents(pub u32);

impl Cents {
    pub const ZERO: Cents = Cents(0);

    /// Subtraction that refuses to go negative.
    pub fn checked_sub(self, other: Cents) -> Option<Cents> {
        self.0.checked_sub(other.0).map(Cents)
    }
}

impl Add for Cents {
    type Output = Cents;
    fn add(self, rhs: Cents) -> Cents {
        Cents(self.0 + rhs.0)
    }
}

impl AddAssign for Cents {
    fn add_assign(&mut self, rhs: Cents) {
        self.0 += rhs.0;
    }
}

impl fmt::Display for Cents {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "${}.{:02}", self.0 / 100, self.0 % 100)
    }
}

impl std::str::FromStr for Cents {
    type Err = String;

    /// Parses a dollar amount such as `1.25`, `$0.65` or `2`.
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let bad = || format!("'{s}' is not a dollar amount (expected e.g. 1.25)");
        let body = s.trim().trim_start_matches('$');
        let (whole, frac) = body.split_once('.').unwrap_or((body, "00"));
        let all_digits = |p: &str| !p.is_empty() && p.bytes().all(|b| b.is_ascii_digit());
        if !all_digits(whole) || frac.len() != 2 || !all_digits(frac) {
            return Err(bad());
        }
        let dollars: u32 = whole.parse().map_err(|_| bad())?;
        let cents: u32 = frac.parse().map_err(|_| bad())?;
        dollars
            .checked_mul(100)
            .and_then(|d| d.checked_add(cents))
            .map(Cents)
            .ok_or_else(bad)
    }
}

/// The coins the machine accepts. Pennies are deliberately not accepted,
/// which is what real machines do and keeps every price a multiple of 5¢.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Coin {
    Nickel,
    Dime,
    Quarter,
    Dollar,
}

impl Coin {
    /// Every accepted coin, largest first.
    pub const ALL: [Coin; 4] = [Coin::Dollar, Coin::Quarter, Coin::Dime, Coin::Nickel];

    pub const fn value(self) -> Cents {
        Cents(match self {
            Coin::Nickel => 5,
            Coin::Dime => 10,
            Coin::Quarter => 25,
            Coin::Dollar => 100,
        })
    }

    /// Position in [`Coin::ALL`]; used to index fixed-size count arrays.
    pub(crate) const fn index(self) -> usize {
        match self {
            Coin::Dollar => 0,
            Coin::Quarter => 1,
            Coin::Dime => 2,
            Coin::Nickel => 3,
        }
    }
}

impl fmt::Display for Coin {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let name = match self {
            Coin::Nickel => "nickel",
            Coin::Dime => "dime",
            Coin::Quarter => "quarter",
            Coin::Dollar => "dollar",
        };
        f.write_str(name)
    }
}

impl std::str::FromStr for Coin {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "n" | "nickel" | "5" => Ok(Coin::Nickel),
            "d" | "dime" | "10" => Ok(Coin::Dime),
            "q" | "quarter" | "25" => Ok(Coin::Quarter),
            "$" | "dollar" | "100" => Ok(Coin::Dollar),
            other => Err(format!(
                "unknown coin '{other}' (use nickel, dime, quarter or dollar)"
            )),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn formats_as_dollars() {
        assert_eq!(Cents(0).to_string(), "$0.00");
        assert_eq!(Cents(5).to_string(), "$0.05");
        assert_eq!(Cents(125).to_string(), "$1.25");
    }

    #[test]
    fn checked_sub_never_underflows() {
        assert_eq!(Cents(10).checked_sub(Cents(15)), None);
        assert_eq!(Cents(15).checked_sub(Cents(10)), Some(Cents(5)));
    }

    #[test]
    fn parses_dollar_amounts() {
        assert_eq!("1.25".parse::<Cents>(), Ok(Cents(125)));
        assert_eq!("$0.65".parse::<Cents>(), Ok(Cents(65)));
        assert_eq!("2".parse::<Cents>(), Ok(Cents(200)));
        for bad in ["", "1.5", "1.234", "-1.00", "abc", ".50", "99999999.00"] {
            assert!(bad.parse::<Cents>().is_err(), "{bad} should not parse");
        }
    }

    #[test]
    fn parses_coin_aliases() {
        assert_eq!("Q".parse::<Coin>(), Ok(Coin::Quarter));
        assert_eq!("dollar".parse::<Coin>(), Ok(Coin::Dollar));
        assert!("penny".parse::<Coin>().is_err());
    }

    #[test]
    fn index_matches_all_order() {
        for (i, coin) in Coin::ALL.iter().enumerate() {
            assert_eq!(coin.index(), i);
        }
    }
}
