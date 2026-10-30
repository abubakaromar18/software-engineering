//! Tests of the public library API, written the way a downstream crate would use it.

use std::error::Error;

use ledger_check::parse::{ParseErrorKind, HEADER};
use ledger_check::validate::Violation;
use ledger_check::{check_str, report, Category, LedgerError, Policy};

#[test]
fn callers_can_match_on_structured_errors() {
    let input = format!("{HEADER}\nt1,2026-01-01,a,1.234,\n");
    let Err(LedgerError::Parse(errs)) = check_str(&input, Policy::default()) else {
        unreachable!("expected a parse error");
    };
    assert!(matches!(
        errs.errors()[0].kind,
        ParseErrorKind::Amount { .. }
    ));
}

#[test]
fn parse_errors_stop_before_validation() {
    // Line 2 overdraws and line 3 is malformed: only the parse error is
    // reported, because rules over half-parsed data would be misleading.
    let input = format!("{HEADER}\nt1,2026-01-01,a,-5,\nt2,nope,a,1,\n");
    let err = check_str(&input, Policy::default()).err();
    assert!(matches!(err, Some(LedgerError::Parse(_))));
}

#[test]
fn rule_errors_are_categorised_as_data() {
    let input = format!("{HEADER}\nt1,2026-01-01,a,-5,\n");
    let err = check_str(&input, Policy::default()).err();
    let Some(err) = err else {
        unreachable!("expected an error")
    };
    assert_eq!(err.category(), Category::Data);
    let LedgerError::Rules(rules) = &err else {
        unreachable!("expected rule errors")
    };
    assert!(matches!(
        rules.errors()[0].violation,
        Violation::Overdraft { .. }
    ));
}

#[test]
fn errors_are_send_sync_and_static() {
    // Lets them cross threads and be boxed as `Box<dyn Error + Send + Sync>`.
    fn assert_bounds<T: Error + Send + Sync + 'static>() {}
    assert_bounds::<LedgerError>();
}

#[test]
fn details_render_full_chain_per_line() {
    let input = format!("{HEADER}\nt1,2026-13-01,a,1,\n");
    let Some(err) = check_str(&input, Policy::default()).err() else {
        unreachable!("expected an error")
    };
    assert_eq!(
        err.details(),
        vec![r#"line 2: invalid date "2026-13-01": month 13 is not between 1 and 12"#]
    );
    assert_eq!(
        report::chain(&err),
        "the file is malformed: 1 malformed line"
    );
}

#[test]
fn boxes_into_dyn_error() {
    fn run() -> Result<(), Box<dyn Error + Send + Sync>> {
        check_str("", Policy::default())?;
        Ok(())
    }
    let err = run().err();
    assert_eq!(
        err.map(|e| e.to_string()),
        Some("the file is malformed".to_owned())
    );
}
