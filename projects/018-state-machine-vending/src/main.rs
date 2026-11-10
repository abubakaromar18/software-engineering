//! Interactive vending machine.
//!
//! Reads one command per line from stdin (so it can also be scripted:
//! `vending --demo < script.txt`). Run with `--demo` to start with stock.
//! The service PIN comes from `VENDING_PIN` (default 1234).

use std::io::{self, BufRead, IsTerminal, Write};
use std::process::ExitCode;

use vending::command::Command;
use vending::session::{AnyMachine, Reply};
use vending::{Cents, MachineConfig, Product, SlotId, VendingMachine};

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let config = config_from_env()?;
    let demo = std::env::args().skip(1).any(|a| a == "--demo");
    let mut machine = if demo {
        demo_machine(config)?
    } else {
        AnyMachine::new(config)
    };

    let stdin = io::stdin();
    let interactive = stdin.is_terminal();
    if interactive {
        println!("Vending machine ready. Type 'help' for commands, 'quit' to leave.");
    }

    let mut lines = stdin.lock().lines();
    loop {
        if interactive {
            print!("[{}] > ", machine.state_name());
            io::stdout().flush()?;
        }
        let Some(line) = lines.next() else { break };
        let line = line?;
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        if trimmed.eq_ignore_ascii_case("quit") {
            break;
        }
        if !interactive {
            println!("> {trimmed}");
        }
        match trimmed.parse::<Command>() {
            Ok(cmd) => {
                let (next, reply) = machine.handle(cmd);
                machine = next;
                match reply {
                    Reply::Done(msg) => println!("{msg}"),
                    Reply::Refused(msg) => println!("✗ {msg}"),
                }
            }
            Err(e) => println!("✗ {e}"),
        }
    }
    Ok(())
}

fn config_from_env() -> Result<MachineConfig, String> {
    let mut config = MachineConfig::default();
    if let Ok(pin) = std::env::var("VENDING_PIN") {
        config.pin = pin
            .parse()
            .map_err(|_| format!("VENDING_PIN must be a number, got '{pin}'"))?;
    }
    Ok(config)
}

/// Stocks a machine through the typed API, showing that setup code is
/// checked by the compiler just like the core.
fn demo_machine(config: MachineConfig) -> Result<AnyMachine, Box<dyn std::error::Error>> {
    let pin = config.pin;
    let mut svc = VendingMachine::new(config).service(pin)?;
    let stock = [
        ("A1", "Cola", 125, 5),
        ("A2", "Sparkling Water", 100, 5),
        ("B1", "Salted Chips", 65, 3),
        ("B2", "Chocolate Bar", 90, 1),
        ("C1", "Gum", 35, 8),
    ];
    for (slot, name, cents, qty) in stock {
        svc.load(
            slot.parse::<SlotId>()?,
            Product::new(name, Cents(cents)),
            qty,
        )?;
    }
    Ok(AnyMachine::Idle(svc.exit()))
}
