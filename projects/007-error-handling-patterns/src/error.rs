//! The library's top-level error type.
//!
//! [`LedgerError`] is the one error type the public API returns. Each variant
//! wraps a lower-level error, and `From` impls let the `?` operator do the
//! wrapping, so call sites stay a single line.

use std::error::Error;
use std::fmt;
use std::io;
use std::path::PathBuf;

use crate::parse::ParseErrors;
use crate::validate::RuleErrors;

/// Everything that can go wrong while checking a ledger.
#[derive(Debug)]
#[non_exhaustive]
pub enum LedgerError {
    /// The file could not be read.
    Read {
        /// The path that was being read.
        path: PathBuf,
        /// The underlying OS error.
        source: io::Error,
    },
    /// The file was read but some lines are malformed.
    Parse(ParseErrors),
    /// Every line parsed but business rules were broken.
    Rules(RuleErrors),
}

/// Broad classification used to choose exit codes and wording.
///
/// Callers match on this rather than on variants, so new variants can be
/// added without breaking them.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Category {
    /// The input file does not exist.
    NotFound,
    /// Some other I/O failure (permissions, a directory, a disk error).
    Io,
    /// The input is present but wrong; the user needs to fix their data.
    Data,
}

impl LedgerError {
    /// Classifies the error.
    #[must_use]
    pub fn category(&self) -> Category {
        match self {
            Self::Read { source, .. } if source.kind() == io::ErrorKind::NotFound => {
                Category::NotFound
            }
            Self::Read { .. } => Category::Io,
            Self::Parse(_) | Self::Rules(_) => Category::Data,
        }
    }

    /// Individual problems behind an aggregate error, each rendered as its
    /// full cause chain. Empty for single errors.
    #[must_use]
    pub fn details(&self) -> Vec<String> {
        match self {
            Self::Read { .. } => Vec::new(),
            Self::Parse(errs) => errs
                .errors()
                .iter()
                .map(|e| crate::report::chain(e))
                .collect(),
            Self::Rules(errs) => errs
                .errors()
                .iter()
                .map(|e| crate::report::chain(e))
                .collect(),
        }
    }
}

impl fmt::Display for LedgerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Read { path, .. } => write!(f, "could not read `{}`", path.display()),
            Self::Parse(_) => f.write_str("the file is malformed"),
            Self::Rules(_) => f.write_str("the ledger breaks business rules"),
        }
    }
}

impl Error for LedgerError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Read { source, .. } => Some(source),
            Self::Parse(e) => Some(e),
            Self::Rules(e) => Some(e),
        }
    }
}

// `From` impls are what make `?` convert errors automatically. There is
// deliberately no `From<io::Error>`: a bare io::Error has no path, so the
// caller must build `Read { path, source }` explicitly.
impl From<ParseErrors> for LedgerError {
    fn from(e: ParseErrors) -> Self {
        Self::Parse(e)
    }
}

impl From<RuleErrors> for LedgerError {
    fn from(e: RuleErrors) -> Self {
        Self::Rules(e)
    }
}
