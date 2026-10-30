//! `ledger` — command-line front end.
//!
//! The binary owns everything the library deliberately leaves out: argument
//! parsing, context messages, rendering, and mapping errors to exit codes.

use std::error::Error;
use std::fmt;
use std::path::PathBuf;
use std::process::ExitCode;

use ledger_check::context::{Context, ResultExt};
use ledger_check::{check_file, report, Category, LedgerError, Policy, Summary};

const USAGE: &str = "\
usage: ledger <command> <file> [--allow-overdraft]

commands:
  check     validate the ledger and print a one-line summary
  balance   validate the ledger and print each account's closing balance
  help      show this message

exit codes:
  0   success           64  bad command-line usage
  65  invalid data      66  input file not found     74  other I/O error";

/// Exit codes from BSD `sysexits.h`, so scripts can tell failures apart.
mod exit {
    pub const USAGE: u8 = 64;
    pub const DATA: u8 = 65;
    pub const NO_INPUT: u8 = 66;
    pub const IO: u8 = 74;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Command {
    Check,
    Balance,
}

#[derive(Debug)]
struct Args {
    command: Command,
    path: PathBuf,
    policy: Policy,
}

/// Errors that only exist at the CLI layer.
#[derive(Debug)]
enum CliError {
    /// The user asked for help; not really an error, but it ends the run early.
    Help,
    /// The arguments were wrong.
    Usage(String),
    /// The library failed, wrapped with what the CLI was doing at the time.
    Ledger(Context<LedgerError>),
}

impl fmt::Display for CliError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Help => f.write_str("help requested"),
            Self::Usage(msg) => f.write_str(msg),
            Self::Ledger(e) => e.fmt(f),
        }
    }
}

impl Error for CliError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            // Delegate so the report skips straight to the context's cause.
            Self::Ledger(e) => e.source(),
            Self::Help | Self::Usage(_) => None,
        }
    }
}

impl From<Context<LedgerError>> for CliError {
    fn from(e: Context<LedgerError>) -> Self {
        Self::Ledger(e)
    }
}

impl CliError {
    fn exit_code(&self) -> u8 {
        match self {
            Self::Help => 0,
            Self::Usage(_) => exit::USAGE,
            // Decide from the *typed* inner error, not from message text.
            Self::Ledger(e) => match e.inner().category() {
                Category::NotFound => exit::NO_INPUT,
                Category::Io => exit::IO,
                Category::Data => exit::DATA,
            },
        }
    }
}

fn parse_args(args: impl IntoIterator<Item = String>) -> Result<Args, CliError> {
    let mut command = None;
    let mut path = None;
    let mut policy = Policy::default();

    for arg in args {
        match arg.as_str() {
            "help" | "-h" | "--help" => return Err(CliError::Help),
            "--allow-overdraft" => policy.allow_overdraft = true,
            flag if flag.starts_with('-') => {
                return Err(CliError::Usage(format!("unknown option `{flag}`")))
            }
            _ if command.is_none() => {
                command = Some(match arg.as_str() {
                    "check" => Command::Check,
                    "balance" => Command::Balance,
                    other => return Err(CliError::Usage(format!("unknown command `{other}`"))),
                });
            }
            _ if path.is_none() => path = Some(PathBuf::from(arg)),
            _ => return Err(CliError::Usage(format!("unexpected argument `{arg}`"))),
        }
    }

    // `Option` -> `Result`: a missing value becomes a usage error.
    let command = command.ok_or_else(|| CliError::Usage("missing command".into()))?;
    let path = path.ok_or_else(|| CliError::Usage("missing <file> argument".into()))?;
    Ok(Args {
        command,
        path,
        policy,
    })
}

fn run(args: Args) -> Result<String, CliError> {
    let summary: Summary = check_file(&args.path, args.policy)
        .with_context(|| format!("could not check `{}`", args.path.display()))?;

    Ok(match args.command {
        Command::Check => {
            let accounts = summary.balances.len();
            format!(
                "ok: {} transactions across {accounts} account{}",
                summary.transactions,
                if accounts == 1 { "" } else { "s" }
            )
        }
        Command::Balance => {
            let width = summary.balances.keys().map(String::len).max().unwrap_or(0);
            summary
                .balances
                .iter()
                .map(|(account, balance)| format!("{account:<width$}  {balance:>12}"))
                .collect::<Vec<_>>()
                .join("\n")
        }
    })
}

/// Renders a failure for stderr: the cause chain, then any per-line details.
fn render(err: &CliError) -> String {
    match err {
        CliError::Help => USAGE.to_owned(),
        CliError::Usage(msg) => format!("error: {msg}\n\n{USAGE}"),
        CliError::Ledger(e) => {
            let mut out = report::tree(err);
            for detail in e.inner().details() {
                out.push_str("\n  - ");
                out.push_str(&detail);
            }
            out
        }
    }
}

fn main() -> ExitCode {
    let result = parse_args(std::env::args().skip(1)).and_then(run);
    match result {
        Ok(output) => {
            println!("{output}");
            ExitCode::SUCCESS
        }
        Err(err) => {
            let code = err.exit_code();
            if code == 0 {
                println!("{}", render(&err));
            } else {
                eprintln!("{}", render(&err));
            }
            ExitCode::from(code)
        }
    }
}

#[cfg(test)]
#[allow(clippy::panic)]
mod tests {
    use super::*;

    fn args(list: &[&str]) -> Result<Args, CliError> {
        parse_args(list.iter().map(|s| (*s).to_owned()))
    }

    #[test]
    fn parses_command_path_and_flag() {
        let Ok(a) = args(&["balance", "--allow-overdraft", "x.csv"]) else {
            panic!("expected valid args")
        };
        assert_eq!(a.command, Command::Balance);
        assert_eq!(a.path, PathBuf::from("x.csv"));
        assert!(a.policy.allow_overdraft);
    }

    #[test]
    fn usage_errors_have_exit_code_64() {
        for bad in [
            &[][..],
            &["check"],
            &["frobnicate", "x"],
            &["check", "x", "y"],
            &["check", "--nope"],
        ] {
            let err = args(bad).err();
            assert!(matches!(err, Some(CliError::Usage(_))), "{bad:?}");
            assert_eq!(err.map(|e| e.exit_code()), Some(exit::USAGE));
        }
    }

    #[test]
    fn help_is_not_a_failure() {
        let err = args(&["check", "--help"]).err();
        assert_eq!(err.map(|e| e.exit_code()), Some(0));
    }
}
