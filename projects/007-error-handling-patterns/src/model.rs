//! Domain types and the *leaf* errors produced when parsing them.
//!
//! Leaf errors describe exactly one thing that went wrong and carry the data
//! needed to explain it. They know nothing about files, line numbers or the
//! CLI; callers higher up add that context.

use std::error::Error;
use std::fmt;
use std::str::FromStr;

/// A monetary amount stored as an integer number of cents.
///
/// Integers avoid floating-point rounding, and `checked_*` arithmetic turns
/// overflow into an error instead of a silent wrap or a panic.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct Cents(pub i64);

impl Cents {
    /// Adds two amounts, returning `None` if the result would overflow.
    #[must_use]
    pub fn checked_add(self, other: Cents) -> Option<Cents> {
        self.0.checked_add(other.0).map(Cents)
    }

    /// True when the amount is below zero.
    #[must_use]
    pub fn is_negative(self) -> bool {
        self.0 < 0
    }
}

impl fmt::Display for Cents {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let sign = if self.0 < 0 { "-" } else { "" };
        let abs = self.0.unsigned_abs();
        // `pad` (rather than `write!`) honours width and alignment flags such
        // as `{:>12}`, so amounts line up in tables.
        f.pad(&format!("{sign}{}.{:02}", abs / 100, abs % 100))
    }
}

/// Why a string could not be read as an amount.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum AmountError {
    /// The string was empty (or only a sign).
    Empty,
    /// A character other than a digit, sign or decimal point appeared.
    InvalidCharacter(char),
    /// More than one `.` appeared.
    MultipleDecimalPoints,
    /// More than two digits followed the decimal point.
    TooManyDecimalPlaces(usize),
    /// The value does not fit in an `i64` number of cents.
    Overflow,
}

impl fmt::Display for AmountError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => f.write_str("no digits"),
            Self::InvalidCharacter(c) => write!(f, "unexpected character {c:?}"),
            Self::MultipleDecimalPoints => f.write_str("more than one decimal point"),
            Self::TooManyDecimalPlaces(n) => write!(f, "{n} decimal places (at most 2 allowed)"),
            Self::Overflow => f.write_str("value is too large"),
        }
    }
}

// Leaf errors have no underlying cause, so the default `source()` (None) is right.
impl Error for AmountError {}

impl FromStr for Cents {
    type Err = AmountError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let (negative, digits) = match s.strip_prefix('-') {
            Some(rest) => (true, rest),
            None => (false, s.strip_prefix('+').unwrap_or(s)),
        };
        if let Some(bad) = digits.chars().find(|c| !c.is_ascii_digit() && *c != '.') {
            return Err(AmountError::InvalidCharacter(bad));
        }

        let mut parts = digits.split('.');
        let whole = parts.next().unwrap_or_default();
        let frac = parts.next();
        if parts.next().is_some() {
            return Err(AmountError::MultipleDecimalPoints);
        }
        let frac = frac.unwrap_or_default();
        if whole.is_empty() && frac.is_empty() {
            return Err(AmountError::Empty);
        }
        if frac.len() > 2 {
            return Err(AmountError::TooManyDecimalPlaces(frac.len()));
        }

        // Every character is now a known ASCII digit, so the only way the
        // numeric conversion can fail is overflow.
        let whole: i64 = if whole.is_empty() {
            0
        } else {
            whole.parse().map_err(|_| AmountError::Overflow)?
        };
        let frac: i64 = format!("{frac:0<2}")
            .parse()
            .map_err(|_| AmountError::Overflow)?;

        let cents = whole
            .checked_mul(100)
            .and_then(|w| w.checked_add(frac))
            .ok_or(AmountError::Overflow)?;
        Ok(Cents(if negative { -cents } else { cents }))
    }
}

/// A calendar date in ISO-8601 `YYYY-MM-DD` form.
///
/// Field order makes the derived `Ord` chronological.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Date {
    year: u16,
    month: u8,
    day: u8,
}

/// Why a string could not be read as a date.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum DateError {
    /// The text is not shaped like `YYYY-MM-DD`.
    Format,
    /// The month is not between 1 and 12.
    MonthOutOfRange(u8),
    /// The day does not exist in that month.
    DayOutOfRange {
        /// The day that was given.
        day: u8,
        /// The last valid day of that month.
        max: u8,
    },
}

impl fmt::Display for DateError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Format => f.write_str("expected YYYY-MM-DD"),
            Self::MonthOutOfRange(m) => write!(f, "month {m} is not between 1 and 12"),
            Self::DayOutOfRange { day, max } => {
                write!(f, "day {day} is out of range (this month has {max} days)")
            }
        }
    }
}

impl Error for DateError {}

impl Date {
    /// Builds a date, validating month and day.
    pub fn new(year: u16, month: u8, day: u8) -> Result<Self, DateError> {
        if !(1..=12).contains(&month) {
            return Err(DateError::MonthOutOfRange(month));
        }
        let max = days_in_month(year, month);
        if day == 0 || day > max {
            return Err(DateError::DayOutOfRange { day, max });
        }
        Ok(Self { year, month, day })
    }
}

fn days_in_month(year: u16, month: u8) -> u8 {
    match month {
        2 if is_leap_year(year) => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    }
}

fn is_leap_year(year: u16) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

impl FromStr for Date {
    type Err = DateError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let bytes = s.as_bytes();
        let shaped = bytes.len() == 10
            && bytes[4] == b'-'
            && bytes[7] == b'-'
            && bytes
                .iter()
                .enumerate()
                .all(|(i, b)| i == 4 || i == 7 || b.is_ascii_digit());
        if !shaped {
            return Err(DateError::Format);
        }
        // The shape check guarantees these slices are all digits, but we still
        // map rather than unwrap: the conversion is fallible by type.
        fn num<T: FromStr>(digits: &str) -> Result<T, DateError> {
            digits.parse().map_err(|_| DateError::Format)
        }
        let year: u16 = num(&s[0..4])?;
        let month: u8 = num(&s[5..7])?;
        let day: u8 = num(&s[8..10])?;
        Date::new(year, month, day)
    }
}

impl fmt::Display for Date {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:04}-{:02}-{:02}", self.year, self.month, self.day)
    }
}

/// One parsed ledger entry. Positive amounts are deposits, negative are withdrawals.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Transaction {
    /// 1-based line number in the source, kept so later errors can point at it.
    pub line: usize,
    /// Unique transaction identifier.
    pub id: String,
    /// Booking date.
    pub date: Date,
    /// Account the amount is booked against.
    pub account: String,
    /// Signed amount.
    pub amount: Cents,
    /// Free-text description (may be empty).
    pub memo: String,
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn parses_amounts() {
        assert_eq!("12.34".parse(), Ok(Cents(1234)));
        assert_eq!("-0.5".parse(), Ok(Cents(-50)));
        assert_eq!("+7".parse(), Ok(Cents(700)));
        assert_eq!(".05".parse(), Ok(Cents(5)));
        assert_eq!("3.".parse(), Ok(Cents(300)));
    }

    #[test]
    fn rejects_bad_amounts_with_specific_reasons() {
        assert_eq!("".parse::<Cents>(), Err(AmountError::Empty));
        assert_eq!("-".parse::<Cents>(), Err(AmountError::Empty));
        assert_eq!(".".parse::<Cents>(), Err(AmountError::Empty));
        assert_eq!(
            "1,000".parse::<Cents>(),
            Err(AmountError::InvalidCharacter(','))
        );
        assert_eq!(
            "1.2.3".parse::<Cents>(),
            Err(AmountError::MultipleDecimalPoints)
        );
        assert_eq!(
            "1.234".parse::<Cents>(),
            Err(AmountError::TooManyDecimalPlaces(3))
        );
        assert_eq!(
            "99999999999999999999".parse::<Cents>(),
            Err(AmountError::Overflow)
        );
        assert_eq!(
            "92233720368547759".parse::<Cents>(),
            Err(AmountError::Overflow)
        );
    }

    #[test]
    fn formats_amounts() {
        assert_eq!(Cents(1234).to_string(), "12.34");
        assert_eq!(Cents(-5).to_string(), "-0.05");
        assert_eq!(Cents(i64::MIN).to_string(), "-92233720368547758.08");
        assert_eq!(format!("[{:>8}]", Cents(150)), "[    1.50]");
    }

    #[test]
    fn checked_add_reports_overflow() {
        assert_eq!(Cents(i64::MAX).checked_add(Cents(1)), None);
        assert_eq!(Cents(1).checked_add(Cents(2)), Some(Cents(3)));
    }

    #[test]
    fn parses_and_validates_dates() {
        let d: Date = "2024-02-29".parse().unwrap();
        assert_eq!(d.to_string(), "2024-02-29");
        assert_eq!(
            "2023-02-29".parse::<Date>(),
            Err(DateError::DayOutOfRange { day: 29, max: 28 })
        );
        assert_eq!(
            "1900-02-29".parse::<Date>(),
            Err(DateError::DayOutOfRange { day: 29, max: 28 })
        );
        assert!("2000-02-29".parse::<Date>().is_ok());
        assert_eq!(
            "2024-13-01".parse::<Date>(),
            Err(DateError::MonthOutOfRange(13))
        );
        assert_eq!(
            "2024-04-31".parse::<Date>(),
            Err(DateError::DayOutOfRange { day: 31, max: 30 })
        );
        assert_eq!("2024/01/01".parse::<Date>(), Err(DateError::Format));
        assert_eq!("24-01-01".parse::<Date>(), Err(DateError::Format));
        assert_eq!(
            "2024-01-00".parse::<Date>(),
            Err(DateError::DayOutOfRange { day: 0, max: 31 })
        );
    }

    #[test]
    fn dates_order_chronologically() {
        let a: Date = "2024-01-31".parse().unwrap();
        let b: Date = "2024-02-01".parse().unwrap();
        assert!(a < b);
    }
}
