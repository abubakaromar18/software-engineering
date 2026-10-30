//! # ledger_check
//!
//! A small ledger validator that exists to show error-handling patterns in
//! Rust. Errors are organised in layers, each wrapping the one below:
//!
//! ```text
//! Context<LedgerError>        "could not check `books.csv`"      (CLI adds this)
//!   └─ LedgerError::Parse      "the file is malformed"             (error.rs)
//!        └─ ParseErrors        "2 malformed lines"                 (parse.rs)
//!             └─ ParseError    "line 3: invalid amount \"1.2.3\""  (parse.rs)
//!                  └─ AmountError "more than one decimal point"    (model.rs)
//! ```
//!
//! The library never panics on bad input and never prints; it returns values
//! and leaves presentation to the caller.

pub mod context;
pub mod error;
pub mod model;
pub mod parse;
pub mod report;
pub mod validate;

use std::fs;
use std::path::Path;

pub use crate::error::{Category, LedgerError};
pub use crate::validate::{Balances, Policy};

/// The result of a successful check.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Summary {
    /// How many transactions were read.
    pub transactions: usize,
    /// Closing balance per account.
    pub balances: Balances,
}

/// Parses and validates ledger text.
///
/// `?` converts `ParseErrors` and `RuleErrors` into `LedgerError` through
/// their `From` impls.
pub fn check_str(input: &str, policy: Policy) -> Result<Summary, LedgerError> {
    let transactions = parse::parse_ledger(input)?;
    let balances = validate::validate(&transactions, policy)?;
    Ok(Summary {
        transactions: transactions.len(),
        balances,
    })
}

/// Reads a file and checks it.
pub fn check_file(path: &Path, policy: Policy) -> Result<Summary, LedgerError> {
    // No `From<io::Error>` exists on purpose, so the path must be attached here.
    let input = fs::read_to_string(path).map_err(|source| LedgerError::Read {
        path: path.to_owned(),
        source,
    })?;
    check_str(&input, policy)
}
