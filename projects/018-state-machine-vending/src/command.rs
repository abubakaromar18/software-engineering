//! Parsing operator/customer text input into commands.
//!
//! This is the untyped edge of the system: anything can be typed at any
//! time, so commands are parsed here without regard to the machine's state.
//! Whether a command is *allowed* is decided by [`crate::session`].

use crate::inventory::SlotId;
use crate::money::{Cents, Coin};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Command {
    Insert(Coin),
    Select(SlotId),
    Cancel,
    Take,
    Service(u32),
    Load {
        slot: SlotId,
        price: Cents,
        quantity: u32,
        name: String,
    },
    Restock {
        slot: SlotId,
        extra: u32,
    },
    Price {
        slot: SlotId,
        price: Cents,
    },
    Float {
        coin: Coin,
        count: u32,
    },
    Withdraw,
    Exit,
    Status,
    Help,
}

pub const HELP: &str = "\
customer:  insert <coin> | select <slot> | cancel | take
operator:  service <pin> | load <slot> <price> <qty> <name...> | restock <slot> <n>
           price <slot> <price> | float <coin> <n> | withdraw | exit
anytime:   status | help | quit
coins: nickel dime quarter dollar (or n d q $)   prices: 1.25";

impl std::str::FromStr for Command {
    type Err = String;

    fn from_str(line: &str) -> Result<Self, Self::Err> {
        let mut words = line.split_whitespace();
        let verb = words.next().ok_or("empty command")?.to_ascii_lowercase();
        let args: Vec<&str> = words.collect();

        let cmd = match (verb.as_str(), args.as_slice()) {
            ("insert" | "i", [coin]) => Command::Insert(coin.parse()?),
            ("select" | "s", [slot]) => Command::Select(slot_arg(slot)?),
            ("cancel", []) => Command::Cancel,
            ("take", []) => Command::Take,
            ("service", [pin]) => Command::Service(num_arg(pin, "PIN")?),
            ("load", [slot, price, qty, name @ ..]) if !name.is_empty() => Command::Load {
                slot: slot_arg(slot)?,
                price: price.parse()?,
                quantity: num_arg(qty, "quantity")?,
                name: name.join(" "),
            },
            ("restock", [slot, n]) => Command::Restock {
                slot: slot_arg(slot)?,
                extra: num_arg(n, "count")?,
            },
            ("price", [slot, price]) => Command::Price {
                slot: slot_arg(slot)?,
                price: price.parse()?,
            },
            ("float", [coin, n]) => Command::Float {
                coin: coin.parse()?,
                count: num_arg(n, "count")?,
            },
            ("withdraw", []) => Command::Withdraw,
            ("exit", []) => Command::Exit,
            ("status", []) => Command::Status,
            ("help" | "?", []) => Command::Help,
            _ => {
                return Err(format!(
                    "could not understand '{}'; type 'help'",
                    line.trim()
                ))
            }
        };
        Ok(cmd)
    }
}

fn slot_arg(s: &str) -> Result<SlotId, String> {
    s.parse()
        .map_err(|e: crate::error::InventoryError| e.to_string())
}

fn num_arg(s: &str, what: &str) -> Result<u32, String> {
    s.parse()
        .map_err(|_| format!("{what} must be a whole number, got '{s}'"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_customer_commands() {
        assert_eq!("insert q".parse(), Ok(Command::Insert(Coin::Quarter)));
        assert_eq!(
            "SELECT a1".parse(),
            Ok(Command::Select("A1".parse().unwrap()))
        );
        assert_eq!(" cancel ".parse(), Ok(Command::Cancel));
    }

    #[test]
    fn parses_multi_word_product_names() {
        assert_eq!(
            "load B2 0.65 5 Salt & Vinegar Chips".parse(),
            Ok(Command::Load {
                slot: "B2".parse().unwrap(),
                price: Cents(65),
                quantity: 5,
                name: "Salt & Vinegar Chips".into(),
            })
        );
    }

    #[test]
    fn reports_bad_arguments() {
        assert!("insert penny"
            .parse::<Command>()
            .unwrap_err()
            .contains("unknown coin"));
        assert!("restock A1 lots"
            .parse::<Command>()
            .unwrap_err()
            .contains("whole number"));
        assert!("load A1 1.00 3".parse::<Command>().is_err());
        assert!("dance".parse::<Command>().unwrap_err().contains("help"));
        assert!("".parse::<Command>().is_err());
    }
}
