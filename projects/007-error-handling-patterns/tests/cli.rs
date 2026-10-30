//! End-to-end tests: run the real `ledger` binary and check stdout, stderr
//! and exit codes, since those are the CLI's contract with scripts.

use std::path::PathBuf;
use std::process::{Command, Output};

fn example(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("examples")
        .join(name)
}

fn ledger(args: &[&str]) -> Output {
    match Command::new(env!("CARGO_BIN_EXE_ledger"))
        .args(args)
        .output()
    {
        Ok(output) => output,
        Err(e) => unreachable!("could not launch ledger binary: {e}"),
    }
}

fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

#[test]
fn check_succeeds_on_valid_ledger() {
    let path = example("household.csv");
    let out = ledger(&["check", path.to_str().unwrap_or_default()]);
    assert_eq!(out.status.code(), Some(0));
    assert_eq!(
        text(&out.stdout).trim(),
        "ok: 6 transactions across 2 accounts"
    );
    assert!(out.stderr.is_empty());
}

#[test]
fn balance_prints_aligned_table() {
    let path = example("household.csv");
    let out = ledger(&["balance", path.to_str().unwrap_or_default()]);
    assert_eq!(out.status.code(), Some(0));
    let stdout = text(&out.stdout);
    let lines: Vec<&str> = stdout.lines().collect();
    assert_eq!(
        lines,
        vec!["checking        915.83", "savings         300.42"]
    );
}

#[test]
fn malformed_file_lists_every_bad_line_with_causes() {
    let path = example("malformed.csv");
    let out = ledger(&["check", path.to_str().unwrap_or_default()]);
    assert_eq!(out.status.code(), Some(65));
    assert!(out.stdout.is_empty());
    let stderr = text(&out.stderr);
    let expected = [
        "error: could not check `",
        "  caused by: the file is malformed",
        "    caused by: 5 malformed lines",
        "  - line 3: invalid date \"2026-02-30\": day 30 is out of range (this month has 28 days)",
        "  - line 4: invalid amount \"$300\": unexpected character '$'",
    ];
    for needle in expected {
        assert!(stderr.contains(needle), "missing {needle:?} in:\n{stderr}");
    }
    assert!(stderr.contains("  - line 5: invalid amount \"1.2.3\": more than one decimal point"));
    assert!(stderr.contains("  - line 6: field `account` is empty"));
    assert!(stderr.contains("  - line 7: expected 5 fields, found 3"));
}

#[test]
fn rule_violations_are_reported_together() {
    let path = example("overdrawn.csv");
    let out = ledger(&["check", path.to_str().unwrap_or_default()]);
    assert_eq!(out.status.code(), Some(65));
    let stderr = text(&out.stderr);
    assert!(stderr.contains("caused by: the ledger breaks business rules"));
    assert!(stderr.contains("caused by: 5 rule violations"));
    assert!(stderr.contains(
        "line 3 (transaction t002): account `checking` would be overdrawn (balance -50.00)"
    ));
    assert!(stderr.contains("line 4 (transaction t002): id `t002` was already used on line 3"));
    // One transaction can break several rules; each is reported.
    assert!(stderr.contains(
        "line 4 (transaction t002): account `checking` would be overdrawn (balance -25.00)"
    ));
    assert!(stderr.contains("line 5 (transaction t003): dated 2026-01-04, which is before the previous entry (2026-01-06)"));
    assert!(stderr.contains("line 5 (transaction t003): amount is zero"));
}

#[test]
fn missing_file_exits_66_and_shows_os_error() {
    let out = ledger(&["check", "definitely/not/here.csv"]);
    assert_eq!(out.status.code(), Some(66));
    let stderr = text(&out.stderr);
    assert!(stderr.starts_with("error: could not check `definitely/not/here.csv`"));
    assert!(stderr.contains("caused by: could not read `definitely/not/here.csv`"));
    // The OS error is the root cause; its exact wording is platform-specific.
    assert_eq!(stderr.lines().count(), 3, "{stderr}");
}

#[test]
fn directory_exits_74() {
    let dir = example("");
    let out = ledger(&["check", dir.to_str().unwrap_or_default()]);
    assert_eq!(out.status.code(), Some(74));
}

#[test]
fn usage_errors_exit_64_with_help() {
    let out = ledger(&["audit", "x.csv"]);
    assert_eq!(out.status.code(), Some(64));
    let stderr = text(&out.stderr);
    assert!(stderr.starts_with("error: unknown command `audit`"));
    assert!(stderr.contains("usage: ledger"));
}

#[test]
fn help_goes_to_stdout_and_succeeds() {
    let out = ledger(&["--help"]);
    assert_eq!(out.status.code(), Some(0));
    assert!(text(&out.stdout).starts_with("usage: ledger"));
}
