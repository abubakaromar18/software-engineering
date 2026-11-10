//! A vending machine built with the **type-state pattern**.
//!
//! The machine's state is part of its type (`VendingMachine<Idle>`,
//! `VendingMachine<Paying>`, …), so calling an operation that is illegal in
//! the current state is a compile error rather than a runtime check. See
//! [`machine`] for the state diagram and `compile_fail` examples.
//!
//! Module layout:
//! - [`money`] / [`coins`]: exact money, coin bags and bounded change-making
//! - [`inventory`]: slots, products and stock limits
//! - [`machine`]: the type-state core
//! - [`command`] / [`session`]: the untyped text edge used by the CLI

pub mod coins;
pub mod command;
pub mod error;
pub mod inventory;
pub mod machine;
pub mod money;
pub mod session;

pub use coins::CoinBag;
pub use error::{InventoryError, Rejected, ServiceError, VendError};
pub use inventory::{Inventory, Product, SlotId};
pub use machine::{MachineConfig, VendingMachine};
pub use money::{Cents, Coin};
