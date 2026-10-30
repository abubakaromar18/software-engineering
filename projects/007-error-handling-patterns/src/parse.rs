//! Turning CSV text into [`Transaction`]s.
//!
//! Two patterns live here:
//!
//! * **Wrapping leaf errors with location.** [`ParseError`] pairs a line
//!   number with a [`ParseErrorKind`]; amount and date failures keep the leaf
//!   error as their `source()` so nothing is lost.
//! * **Accumulating instead of failing fast.** A user fixing a file wants every
//!   problem at once, so [`parse_ledger`] keeps going and returns all failures
//!   as one [`ParseErrors`] value.

use std::error::Error;
use std::fmt;

use crate::model::{AmountError, Cents, Date, DateError, Transaction};

/// The header every ledger file must start with.
pub const HEADER: &str = "id,date,account,amount,memo";
const FIELD_COUNT: usize = 5;

/// What went wrong on a single line.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum ParseErrorKind {
    /// The input contained no header line at all.
    MissingHeader,
    /// The first line was not [`HEADER`].
    BadHeader {
        /// The header line that was found instead.
        found: String,
    },
    /// The line did not split into the expected number of fields.
    FieldCount {
        /// How many fields were found.
        found: usize,
    },
    /// A required field was blank.
    EmptyField(&'static str),
    /// The `date` field was invalid.
    Date {
        /// The raw text.
        value: String,
        /// Why it was rejected.
        source: DateError,
    },
    /// The `amount` field was invalid.
    Amount {
        /// The raw text.
        value: String,
        /// Why it was rejected.
        source: AmountError,
    },
}

/// A failure tied to a 1-based line number.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParseError {
    /// 1-based line number.
    pub line: usize,
    /// What went wrong.
    pub kind: ParseErrorKind,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "line {}: ", self.line)?;
        // Display describes *this* layer only; the cause is reachable via
        // `source()`. Repeating it here would print it twice in a report.
        match &self.kind {
            ParseErrorKind::MissingHeader => {
                write!(f, "input is empty, expected header `{HEADER}`")
            }
            ParseErrorKind::BadHeader { found } => {
                write!(f, "expected header `{HEADER}`, found `{found}`")
            }
            ParseErrorKind::FieldCount { found } => {
                write!(f, "expected {FIELD_COUNT} fields, found {found}")
            }
            ParseErrorKind::EmptyField(name) => write!(f, "field `{name}` is empty"),
            ParseErrorKind::Date { value, .. } => write!(f, "invalid date {value:?}"),
            ParseErrorKind::Amount { value, .. } => write!(f, "invalid amount {value:?}"),
        }
    }
}

impl Error for ParseError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match &self.kind {
            ParseErrorKind::Date { source, .. } => Some(source),
            ParseErrorKind::Amount { source, .. } => Some(source),
            _ => None,
        }
    }
}

/// Every [`ParseError`] found in one input. Never empty.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParseErrors(Vec<ParseError>);

impl ParseErrors {
    /// The individual errors, in line order.
    #[must_use]
    pub fn errors(&self) -> &[ParseError] {
        &self.0
    }
}

impl fmt::Display for ParseErrors {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let n = self.0.len();
        write!(f, "{n} malformed line{}", if n == 1 { "" } else { "s" })
    }
}

// An aggregate has many causes, but `source()` can return only one, so it
// returns none and exposes the full list through `errors()` instead.
impl Error for ParseErrors {}

/// Parses one data line. `line` is used only for error reporting.
pub fn parse_line(line: usize, text: &str) -> Result<Transaction, ParseError> {
    let err = |kind| ParseError { line, kind };

    // `splitn` keeps any commas inside the final memo field.
    let fields: Vec<&str> = text.splitn(FIELD_COUNT, ',').map(str::trim).collect();
    let [id, date, account, amount, memo] = fields[..] else {
        return Err(err(ParseErrorKind::FieldCount {
            found: fields.len(),
        }));
    };

    let required = |name, value: &str| {
        if value.is_empty() {
            Err(err(ParseErrorKind::EmptyField(name)))
        } else {
            Ok(())
        }
    };
    required("id", id)?;
    required("date", date)?;
    required("account", account)?;
    required("amount", amount)?;

    // `map_err` converts each leaf error into this layer's error while
    // keeping the original as the source.
    let parsed_date: Date = date.parse().map_err(|source| {
        err(ParseErrorKind::Date {
            value: date.to_owned(),
            source,
        })
    })?;
    let parsed_amount: Cents = amount.parse().map_err(|source| {
        err(ParseErrorKind::Amount {
            value: amount.to_owned(),
            source,
        })
    })?;

    Ok(Transaction {
        line,
        id: id.to_owned(),
        date: parsed_date,
        account: account.to_owned(),
        amount: parsed_amount,
        memo: memo.to_owned(),
    })
}

/// Parses a whole ledger, collecting *every* bad line rather than stopping at the first.
///
/// Blank lines and lines starting with `#` are ignored.
pub fn parse_ledger(input: &str) -> Result<Vec<Transaction>, ParseErrors> {
    let mut lines = input
        .lines()
        .enumerate()
        .map(|(i, text)| (i + 1, text.trim()))
        .filter(|(_, text)| !text.is_empty() && !text.starts_with('#'));

    // A bad header means every other "error" would be noise, so this one
    // check does fail fast.
    match lines.next() {
        None => {
            return Err(ParseErrors(vec![ParseError {
                line: 1,
                kind: ParseErrorKind::MissingHeader,
            }]))
        }
        Some((_, header)) if header.eq_ignore_ascii_case(HEADER) => {}
        Some((line, header)) => {
            return Err(ParseErrors(vec![ParseError {
                line,
                kind: ParseErrorKind::BadHeader {
                    found: header.to_owned(),
                },
            }]))
        }
    }

    let (ok, failed): (Vec<_>, Vec<_>) = lines
        .map(|(line, text)| parse_line(line, text))
        .partition(Result::is_ok);

    if failed.is_empty() {
        Ok(ok.into_iter().flatten().collect())
    } else {
        Err(ParseErrors(
            failed.into_iter().filter_map(Result::err).collect(),
        ))
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn parses_a_valid_line_and_keeps_commas_in_memo() {
        let tx = parse_line(2, "t1, 2024-01-05 ,checking,12.50,rent, January").unwrap();
        assert_eq!(tx.id, "t1");
        assert_eq!(tx.amount, Cents(1250));
        assert_eq!(tx.memo, "rent, January");
        assert_eq!(tx.line, 2);
    }

    #[test]
    fn reports_field_count() {
        let e = parse_line(3, "t1,2024-01-05,checking").unwrap_err();
        assert_eq!(e.kind, ParseErrorKind::FieldCount { found: 3 });
        assert_eq!(e.to_string(), "line 3: expected 5 fields, found 3");
    }

    #[test]
    fn reports_empty_required_field() {
        let e = parse_line(4, "t1,2024-01-05,,1.00,").unwrap_err();
        assert_eq!(e.kind, ParseErrorKind::EmptyField("account"));
    }

    #[test]
    fn keeps_leaf_error_as_source() {
        let e = parse_line(5, "t1,2024-01-05,checking,1.2.3,").unwrap_err();
        assert_eq!(e.to_string(), r#"line 5: invalid amount "1.2.3""#);
        let source = e.source().unwrap();
        assert_eq!(source.to_string(), "more than one decimal point");
        // The source can be recovered as its concrete type.
        assert_eq!(
            source.downcast_ref::<AmountError>(),
            Some(&AmountError::MultipleDecimalPoints)
        );
    }

    #[test]
    fn collects_all_errors() {
        let input = format!(
            "{HEADER}\nt1,2024-01-01,a,1.00,\nt2,bad,a,1.00,\n\n# note\nt3,2024-01-03,a,x,\n"
        );
        let errs = parse_ledger(&input).unwrap_err();
        let lines: Vec<usize> = errs.errors().iter().map(|e| e.line).collect();
        assert_eq!(lines, vec![3, 6]);
        assert_eq!(errs.to_string(), "2 malformed lines");
    }

    #[test]
    fn rejects_missing_or_wrong_header() {
        let e = parse_ledger("\n# only comments\n").unwrap_err();
        assert_eq!(e.errors()[0].kind, ParseErrorKind::MissingHeader);

        let e = parse_ledger("\nid,when,account\nt1,2024-01-01,a,1,\n").unwrap_err();
        assert_eq!(e.errors().len(), 1);
        assert_eq!(e.errors()[0].line, 2);
        assert!(matches!(
            e.errors()[0].kind,
            ParseErrorKind::BadHeader { .. }
        ));
    }

    #[test]
    fn parses_valid_ledger() {
        let input = format!("{HEADER}\nt1,2024-01-01,a,1.00,\nt2,2024-01-02,b,-0.50,x\n");
        let txs = parse_ledger(&input).unwrap();
        assert_eq!(txs.len(), 2);
        assert_eq!(txs[1].line, 3);
    }
}
