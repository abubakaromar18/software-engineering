//! Business rules over parsed transactions.
//!
//! Parsing proves each line is *well-formed*; validation proves the ledger as
//! a whole *makes sense*. Keeping them as separate error types lets callers
//! (and exit codes) tell "your file is garbled" apart from "your books don't
//! balance".

use std::collections::{BTreeMap, HashMap};
use std::error::Error;
use std::fmt;

use crate::model::{Cents, Date, Transaction};

/// Options that change which rules apply.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Policy {
    /// When true, account balances may go below zero.
    pub allow_overdraft: bool,
}

/// A broken business rule.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum Violation {
    /// Two transactions share an id.
    DuplicateId {
        /// The repeated id.
        id: String,
        /// Line of the first occurrence.
        first_line: usize,
    },
    /// A transaction is dated before the one preceding it.
    OutOfOrder {
        /// This transaction's date.
        date: Date,
        /// The later date that came before it.
        previous: Date,
    },
    /// A transaction has a zero amount.
    ZeroAmount,
    /// A withdrawal would take the account below zero.
    Overdraft {
        /// The account.
        account: String,
        /// The balance after the withdrawal.
        balance: Cents,
    },
    /// The running balance no longer fits in an `i64`.
    BalanceOverflow {
        /// The account.
        account: String,
    },
}

/// A [`Violation`] located at the offending transaction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleError {
    /// Line of the transaction that broke the rule.
    pub line: usize,
    /// Id of that transaction.
    pub id: String,
    /// Which rule was broken.
    pub violation: Violation,
}

impl fmt::Display for RuleError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "line {} (transaction {}): ", self.line, self.id)?;
        match &self.violation {
            Violation::DuplicateId { id, first_line } => {
                write!(f, "id `{id}` was already used on line {first_line}")
            }
            Violation::OutOfOrder { date, previous } => {
                write!(
                    f,
                    "dated {date}, which is before the previous entry ({previous})"
                )
            }
            Violation::ZeroAmount => f.write_str("amount is zero"),
            Violation::Overdraft { account, balance } => {
                write!(
                    f,
                    "account `{account}` would be overdrawn (balance {balance})"
                )
            }
            Violation::BalanceOverflow { account } => {
                write!(f, "balance of account `{account}` overflowed")
            }
        }
    }
}

impl Error for RuleError {}

/// Every [`RuleError`] found in one ledger. Never empty.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleErrors(Vec<RuleError>);

impl RuleErrors {
    /// The individual errors, in line order.
    #[must_use]
    pub fn errors(&self) -> &[RuleError] {
        &self.0
    }
}

impl fmt::Display for RuleErrors {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let n = self.0.len();
        write!(f, "{n} rule violation{}", if n == 1 { "" } else { "s" })
    }
}

impl Error for RuleErrors {}

/// Final per-account balances, sorted by account name.
pub type Balances = BTreeMap<String, Cents>;

/// Checks every rule against every transaction and returns the closing balances.
///
/// Like parsing, this collects all violations instead of stopping at the first.
pub fn validate(transactions: &[Transaction], policy: Policy) -> Result<Balances, RuleErrors> {
    let mut balances = Balances::new();
    let mut seen_ids: HashMap<&str, usize> = HashMap::new();
    let mut previous_date: Option<Date> = None;
    let mut errors = Vec::new();

    for tx in transactions {
        let mut report = |violation| {
            errors.push(RuleError {
                line: tx.line,
                id: tx.id.clone(),
                violation,
            });
        };

        if let Some(&first_line) = seen_ids.get(tx.id.as_str()) {
            report(Violation::DuplicateId {
                id: tx.id.clone(),
                first_line,
            });
        } else {
            seen_ids.insert(&tx.id, tx.line);
        }

        match previous_date {
            Some(previous) if tx.date < previous => {
                report(Violation::OutOfOrder {
                    date: tx.date,
                    previous,
                });
            }
            _ => previous_date = Some(tx.date),
        }

        if tx.amount == Cents(0) {
            report(Violation::ZeroAmount);
            continue;
        }

        let balance = balances.entry(tx.account.clone()).or_default();
        // `Option` -> error: `checked_add` returns `None` on overflow and we
        // turn that into a domain-specific violation.
        match balance.checked_add(tx.amount) {
            None => report(Violation::BalanceOverflow {
                account: tx.account.clone(),
            }),
            Some(next) => {
                *balance = next;
                if next.is_negative() && !policy.allow_overdraft {
                    report(Violation::Overdraft {
                        account: tx.account.clone(),
                        balance: next,
                    });
                }
            }
        }
    }

    if errors.is_empty() {
        Ok(balances)
    } else {
        Err(RuleErrors(errors))
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn tx(line: usize, id: &str, date: &str, account: &str, amount: i64) -> Transaction {
        Transaction {
            line,
            id: id.into(),
            date: date.parse().unwrap(),
            account: account.into(),
            amount: Cents(amount),
            memo: String::new(),
        }
    }

    #[test]
    fn computes_balances() {
        let txs = [
            tx(2, "a", "2024-01-01", "checking", 10_000),
            tx(3, "b", "2024-01-02", "checking", -2_500),
            tx(4, "c", "2024-01-02", "savings", 500),
        ];
        let balances = validate(&txs, Policy::default()).unwrap();
        assert_eq!(balances["checking"], Cents(7_500));
        assert_eq!(balances["savings"], Cents(500));
    }

    #[test]
    fn collects_every_violation() {
        let txs = [
            tx(2, "a", "2024-01-05", "checking", 100),
            tx(3, "a", "2024-01-06", "checking", 100),
            tx(4, "b", "2024-01-01", "checking", 100),
            tx(5, "c", "2024-01-07", "checking", 0),
            tx(6, "d", "2024-01-08", "checking", -1_000),
        ];
        let errs = validate(&txs, Policy::default()).unwrap_err();
        let got: Vec<_> = errs
            .errors()
            .iter()
            .map(|e| (e.line, &e.violation))
            .collect();
        assert_eq!(
            got,
            vec![
                (
                    3,
                    &Violation::DuplicateId {
                        id: "a".into(),
                        first_line: 2
                    }
                ),
                (
                    4,
                    &Violation::OutOfOrder {
                        date: "2024-01-01".parse().unwrap(),
                        previous: "2024-01-06".parse().unwrap()
                    }
                ),
                (5, &Violation::ZeroAmount),
                (
                    6,
                    &Violation::Overdraft {
                        account: "checking".into(),
                        balance: Cents(-700)
                    }
                ),
            ]
        );
        assert_eq!(errs.to_string(), "4 rule violations");
    }

    #[test]
    fn policy_can_allow_overdraft() {
        let txs = [tx(2, "a", "2024-01-01", "checking", -100)];
        assert!(validate(&txs, Policy::default()).is_err());
        let balances = validate(
            &txs,
            Policy {
                allow_overdraft: true,
            },
        )
        .unwrap();
        assert_eq!(balances["checking"], Cents(-100));
    }

    #[test]
    fn reports_overflow_instead_of_panicking() {
        let txs = [
            tx(2, "a", "2024-01-01", "big", i64::MAX),
            tx(3, "b", "2024-01-02", "big", 1),
        ];
        let errs = validate(&txs, Policy::default()).unwrap_err();
        assert_eq!(
            errs.errors()[0].violation,
            Violation::BalanceOverflow {
                account: "big".into()
            }
        );
    }
}
