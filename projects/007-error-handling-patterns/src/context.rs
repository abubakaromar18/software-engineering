//! Context wrapping: adding "what were we doing?" to an error without losing it.
//!
//! This is the core idea behind `anyhow::Context`, written out by hand and
//! kept *typed*: `Context<E>` still knows its inner error is an `E`, so a
//! caller can wrap an error for display and still inspect it to pick an exit
//! code.

use std::error::Error;
use std::fmt;

/// An error plus a message describing the operation that failed.
#[derive(Debug)]
pub struct Context<E> {
    message: String,
    source: E,
}

impl<E> Context<E> {
    /// Wraps `source` with `message`.
    pub fn new(message: impl Into<String>, source: E) -> Self {
        Self {
            message: message.into(),
            source,
        }
    }

    /// The wrapped error.
    pub fn inner(&self) -> &E {
        &self.source
    }

    /// Unwraps back to the original error, discarding the message.
    pub fn into_inner(self) -> E {
        self.source
    }
}

impl<E> fmt::Display for Context<E> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}

impl<E: Error + 'static> Error for Context<E> {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        Some(&self.source)
    }
}

/// Adds `.context(..)` and `.with_context(..)` to any `Result`.
pub trait ResultExt<T, E> {
    /// Wraps the error with a fixed message.
    fn context(self, message: impl Into<String>) -> Result<T, Context<E>>;

    /// Wraps the error with a message built lazily, so formatting costs
    /// nothing on the success path.
    fn with_context<M, F>(self, f: F) -> Result<T, Context<E>>
    where
        M: Into<String>,
        F: FnOnce() -> M;
}

impl<T, E> ResultExt<T, E> for Result<T, E> {
    fn context(self, message: impl Into<String>) -> Result<T, Context<E>> {
        self.map_err(|source| Context::new(message, source))
    }

    fn with_context<M, F>(self, f: F) -> Result<T, Context<E>>
    where
        M: Into<String>,
        F: FnOnce() -> M,
    {
        self.map_err(|source| Context::new(f(), source))
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use crate::model::{AmountError, Cents};

    #[test]
    fn wraps_and_preserves_the_source() {
        let r: Result<Cents, _> = "1.2.3".parse::<Cents>().context("reading the fee");
        let e = r.unwrap_err();
        assert_eq!(e.to_string(), "reading the fee");
        assert_eq!(e.inner(), &AmountError::MultipleDecimalPoints);
        assert_eq!(
            e.source().unwrap().to_string(),
            "more than one decimal point"
        );
        assert_eq!(e.into_inner(), AmountError::MultipleDecimalPoints);
    }

    #[test]
    fn with_context_is_lazy() {
        let mut called = false;
        let r: Result<i32, Context<AmountError>> = Ok::<_, AmountError>(1).with_context(|| {
            called = true;
            "never built"
        });
        assert_eq!(r.unwrap(), 1);
        assert!(!called);
    }

    #[test]
    fn contexts_nest() {
        let e = Err::<(), _>(AmountError::Empty)
            .context("parsing amount")
            .context("loading invoice 7")
            .unwrap_err();
        assert_eq!(
            crate::report::chain(&e),
            "loading invoice 7: parsing amount: no digits"
        );
    }
}
