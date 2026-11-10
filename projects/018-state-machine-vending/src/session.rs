//! Bridges untyped input to the type-state core.
//!
//! Text commands can arrive in any order, so at the edge of the program the
//! state must be known at runtime. `AnyMachine` is that runtime view: an enum
//! with one variant per state. Each `match` arm below holds a concretely
//! typed machine, so inside an arm the compiler still enforces which
//! operations are legal; the only place a "not allowed now" message can be
//! produced is the explicit fallback arm.

use crate::command::{Command, HELP};
use crate::error::VendError;
use crate::machine::{Dispensing, Idle, MachineConfig, Maintenance, Paying, VendingMachine};
use std::fmt::Write as _;

pub enum AnyMachine {
    Idle(VendingMachine<Idle>),
    Paying(VendingMachine<Paying>),
    Dispensing(VendingMachine<Dispensing>),
    Maintenance(VendingMachine<Maintenance>),
}

/// The result of handling one command.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Reply {
    /// The command was carried out.
    Done(String),
    /// The command was understood but could not be carried out.
    Refused(String),
}

impl Reply {
    pub fn message(&self) -> &str {
        match self {
            Reply::Done(m) | Reply::Refused(m) => m,
        }
    }
}

impl AnyMachine {
    pub fn new(config: MachineConfig) -> Self {
        AnyMachine::Idle(VendingMachine::new(config))
    }

    pub fn state_name(&self) -> &'static str {
        match self {
            AnyMachine::Idle(_) => "idle",
            AnyMachine::Paying(_) => "paying",
            AnyMachine::Dispensing(_) => "dispensing",
            AnyMachine::Maintenance(_) => "maintenance",
        }
    }

    /// Applies one command, returning the machine in its (possibly new)
    /// state together with a reply for the user.
    pub fn handle(self, cmd: Command) -> (AnyMachine, Reply) {
        use AnyMachine as M;
        use Reply::{Done, Refused};

        match (self, cmd) {
            (m, Command::Help) => (m, Done(HELP.to_string())),
            (m, Command::Status) => {
                let text = m.status();
                (m, Done(text))
            }

            // ── Idle ────────────────────────────────────────────────────
            (M::Idle(m), Command::Insert(coin)) => {
                let m = m.insert(coin);
                let msg = format!("credit {}", m.credit());
                (M::Paying(m), Done(msg))
            }
            (M::Idle(m), Command::Service(pin)) => match m.service(pin) {
                Ok(m) => (M::Maintenance(m), Done("service panel open".into())),
                Err(r) => (M::Idle(r.machine), Refused(r.error.to_string())),
            },

            // ── Paying ──────────────────────────────────────────────────
            (M::Paying(m), Command::Insert(coin)) => {
                let m = m.insert(coin);
                let msg = format!("credit {}", m.credit());
                (M::Paying(m), Done(msg))
            }
            (M::Paying(m), Command::Select(slot)) => match m.select(slot) {
                Ok(d) => {
                    let msg = format!(
                        "dispensed {}; change: {} — type 'take'",
                        d.product().name,
                        d.change()
                    );
                    (M::Dispensing(d), Done(msg))
                }
                Err(r) => {
                    // Insufficient-credit errors already state the credit.
                    let msg = match r.error {
                        VendError::InsufficientCredit { .. } => r.error.to_string(),
                        _ => format!("{} (credit {})", r.error, r.machine.credit()),
                    };
                    (M::Paying(r.machine), Refused(msg))
                }
            },
            (M::Paying(m), Command::Cancel) => {
                let (idle, refund) = m.cancel();
                (M::Idle(idle), Done(format!("returned {refund}")))
            }

            // ── Dispensing ──────────────────────────────────────────────
            (M::Dispensing(m), Command::Take) => {
                let (idle, product, change) = m.collect();
                (
                    M::Idle(idle),
                    Done(format!("you took {} and {}", product.name, change)),
                )
            }

            // ── Maintenance ─────────────────────────────────────────────
            (
                M::Maintenance(mut m),
                Command::Load {
                    slot,
                    price,
                    quantity,
                    name,
                },
            ) => {
                let reply = match m.load(slot, crate::Product::new(name, price), quantity) {
                    Ok(()) => Done(format!("loaded {slot}")),
                    Err(e) => Refused(e.to_string()),
                };
                (M::Maintenance(m), reply)
            }
            (M::Maintenance(mut m), Command::Restock { slot, extra }) => {
                let reply = match m.restock(slot, extra) {
                    Ok(qty) => Done(format!("{slot} now holds {qty}")),
                    Err(e) => Refused(e.to_string()),
                };
                (M::Maintenance(m), reply)
            }
            (M::Maintenance(mut m), Command::Price { slot, price }) => {
                let reply = match m.set_price(slot, price) {
                    Ok(()) => Done(format!("{slot} now costs {price}")),
                    Err(e) => Refused(e.to_string()),
                };
                (M::Maintenance(m), reply)
            }
            (M::Maintenance(mut m), Command::Float { coin, count }) => {
                m.add_float(coin, count);
                let msg = format!("cash box now {}", m.cash_on_hand());
                (M::Maintenance(m), Done(msg))
            }
            (M::Maintenance(mut m), Command::Withdraw) => {
                let cash = m.withdraw_cash();
                (M::Maintenance(m), Done(format!("withdrew {cash}")))
            }
            (M::Maintenance(m), Command::Exit) => {
                (M::Idle(m.exit()), Done("service panel closed".into()))
            }

            // ── Everything else is a transition this state does not have ─
            (m, cmd) => {
                let msg = format!("cannot {} while {}", verb(&cmd), m.state_name());
                (m, Refused(msg))
            }
        }
    }

    fn status(&self) -> String {
        let (inventory, cash, revenue, sold) = match self {
            AnyMachine::Idle(m) => (
                m.inventory(),
                m.cash_on_hand(),
                m.revenue(),
                m.sales().len(),
            ),
            AnyMachine::Paying(m) => (
                m.inventory(),
                m.cash_on_hand(),
                m.revenue(),
                m.sales().len(),
            ),
            AnyMachine::Dispensing(m) => (
                m.inventory(),
                m.cash_on_hand(),
                m.revenue(),
                m.sales().len(),
            ),
            AnyMachine::Maintenance(m) => (
                m.inventory(),
                m.cash_on_hand(),
                m.revenue(),
                m.sales().len(),
            ),
        };
        let mut out = format!("state: {}", self.state_name());
        if let AnyMachine::Paying(m) = self {
            let _ = write!(out, " (credit {})", m.credit());
        }
        let _ = write!(out, "\ncash box: {cash}  sales: {sold}  revenue: {revenue}");
        if inventory.iter().next().is_none() {
            out.push_str("\n(no products loaded)");
        }
        for (id, slot) in inventory.iter() {
            let _ = write!(
                out,
                "\n  {id}  {:<20} {:>6}  ×{}",
                slot.product.name, slot.product.price, slot.quantity
            );
        }
        out
    }
}

fn verb(cmd: &Command) -> &'static str {
    match cmd {
        Command::Insert(_) => "insert coins",
        Command::Select(_) => "select a product",
        Command::Cancel => "cancel",
        Command::Take => "take anything",
        Command::Service(_) => "open the service panel",
        Command::Load { .. } => "load products",
        Command::Restock { .. } => "restock",
        Command::Price { .. } => "change prices",
        Command::Float { .. } => "add float",
        Command::Withdraw => "withdraw cash",
        Command::Exit => "exit service mode",
        Command::Status | Command::Help => "do that",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(m: AnyMachine, line: &str) -> (AnyMachine, Reply) {
        m.handle(line.parse().expect("valid command"))
    }

    #[test]
    fn refuses_commands_the_state_lacks() {
        let m = AnyMachine::new(MachineConfig::default());
        let (m, reply) = run(m, "select A1");
        assert_eq!(
            reply,
            Reply::Refused("cannot select a product while idle".into())
        );
        let (m, _) = run(m, "insert q");
        let (m, reply) = run(m, "service 1234");
        assert_eq!(
            reply,
            Reply::Refused("cannot open the service panel while paying".into())
        );
        assert_eq!(m.state_name(), "paying");
    }

    #[test]
    fn full_session() {
        let mut m = AnyMachine::new(MachineConfig::default());
        for line in ["service 1234", "load A1 0.65 3 Chips", "exit", "insert $"] {
            let (next, reply) = run(m, line);
            assert!(matches!(reply, Reply::Done(_)), "{line}: {reply:?}");
            m = next;
        }
        let (m, reply) = run(m, "select A1");
        assert_eq!(
            reply.message(),
            "dispensed Chips; change: 1×quarter, 1×dime ($0.35) — type 'take'"
        );
        let (m, reply) = run(m, "take");
        assert!(reply.message().starts_with("you took Chips"));
        let (_, reply) = run(m, "status");
        assert!(reply.message().contains("A1  Chips"));
        assert!(reply.message().contains("sales: 1"));
    }

    #[test]
    fn failed_select_stays_in_paying() {
        let m = AnyMachine::new(MachineConfig::default());
        let (m, _) = run(m, "insert d");
        let (m, reply) = run(m, "select C3");
        assert!(matches!(reply, Reply::Refused(_)));
        assert_eq!(m.state_name(), "paying");
        let (m, reply) = run(m, "cancel");
        assert_eq!(reply.message(), "returned 1×dime ($0.10)");
        assert_eq!(m.state_name(), "idle");
    }
}
