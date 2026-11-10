//! Runs the compiled binary against the example script.

use std::io::Write;
use std::process::{Command, Stdio};

fn run_cli(args: &[&str], input: &str, env: &[(&str, &str)]) -> (bool, String, String) {
    let mut child = Command::new(env!("CARGO_BIN_EXE_vending"))
        .args(args)
        .envs(env.iter().copied())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("binary runs");
    child
        .stdin
        .take()
        .unwrap()
        .write_all(input.as_bytes())
        .unwrap();
    let out = child.wait_with_output().unwrap();
    (
        out.status.success(),
        String::from_utf8(out.stdout).unwrap(),
        String::from_utf8(out.stderr).unwrap(),
    )
}

#[test]
fn demo_script_produces_expected_transcript() {
    let script = include_str!("../examples/demo.txt");
    let (ok, stdout, _) = run_cli(&["--demo"], script, &[]);
    assert!(ok);
    for expected in [
        "✗ cannot select a product while idle",
        "✗ price is $1.25 but credit is only $1.00\n",
        "dispensed Cola; change: no coins — type 'take'",
        "✗ cannot open the service panel while dispensing",
        "you took Cola and no coins",
        "✗ incorrect service PIN",
        "B2 now holds 5",
        "C1 now costs $0.40",
        "✗ cannot return $1.60 in change; please use exact change (credit $2.00)",
        "returned 2×dollar ($2.00)",
        "sales: 2",
    ] {
        assert!(
            stdout.contains(expected),
            "missing {expected:?} in:\n{stdout}"
        );
    }
}

#[test]
fn bad_pin_env_var_fails_fast() {
    let (ok, _, stderr) = run_cli(&[], "", &[("VENDING_PIN", "abc")]);
    assert!(!ok);
    assert!(stderr.contains("VENDING_PIN must be a number"));
}
