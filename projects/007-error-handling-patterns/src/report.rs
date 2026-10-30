//! Rendering errors for humans by walking the `source()` chain.
//!
//! Each layer's `Display` describes only itself, so a report is just the
//! layers joined together. This is what `anyhow`'s `{:#}` and `{:?}` do.

use std::error::Error;
use std::iter;

/// Iterates over an error and each of its causes, outermost first.
pub fn causes<'a>(
    err: &'a (dyn Error + 'static),
) -> impl Iterator<Item = &'a (dyn Error + 'static)> {
    let mut next = Some(err);
    iter::from_fn(move || {
        let current = next?;
        next = current.source();
        Some(current)
    })
}

/// One-line form: `outer: middle: root`.
#[must_use]
pub fn chain(err: &(dyn Error + 'static)) -> String {
    causes(err)
        .map(ToString::to_string)
        .collect::<Vec<_>>()
        .join(": ")
}

/// Multi-line form with a `caused by:` line per cause.
#[must_use]
pub fn tree(err: &(dyn Error + 'static)) -> String {
    causes(err)
        .enumerate()
        .map(|(depth, e)| {
            if depth == 0 {
                format!("error: {e}")
            } else {
                format!("{}caused by: {e}", "  ".repeat(depth))
            }
        })
        .collect::<Vec<_>>()
        .join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::ResultExt;
    use crate::model::AmountError;

    #[test]
    fn renders_single_error() {
        assert_eq!(chain(&AmountError::Empty), "no digits");
        assert_eq!(tree(&AmountError::Empty), "error: no digits");
    }

    #[test]
    fn renders_nested_errors() {
        let e = Err::<(), _>(AmountError::Overflow)
            .context("inner")
            .context("outer")
            .err();
        let Some(e) = e else { return };
        assert_eq!(causes(&e).count(), 3);
        assert_eq!(
            tree(&e),
            "error: outer\n  caused by: inner\n    caused by: value is too large"
        );
    }
}
