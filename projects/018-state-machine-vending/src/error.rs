//! Error types.
//!
//! Note what is *absent*: there is no `InvalidTransition` / `WrongState`
//! error. Those are compile errors in this design, so the only failures left
//! to model at runtime are genuine business conditions.

use crate::inventory::SlotId;
use crate::money::Cents;
use std::error::Error;
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InventoryError {
    InvalidSlotId(String),
    UnknownSlot(SlotId),
    SoldOut(SlotId),
    OverCapacity { slot: SlotId, capacity: u32 },
    InvalidPrice(Cents),
}

impl fmt::Display for InventoryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidSlotId(s) => write!(f, "'{s}' is not a slot id (expected e.g. A1)"),
            Self::UnknownSlot(id) => write!(f, "slot {id} is empty or does not exist"),
            Self::SoldOut(id) => write!(f, "slot {id} is sold out"),
            Self::OverCapacity { slot, capacity } => {
                write!(f, "slot {slot} holds at most {capacity} items")
            }
            Self::InvalidPrice(p) => write!(f, "price {p} must be positive and a multiple of 5¢"),
        }
    }
}

impl Error for InventoryError {}

/// Why a selection could not be vended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VendError {
    Inventory(InventoryError),
    InsufficientCredit {
        price: Cents,
        credit: Cents,
    },
    /// The machine cannot return the exact change owed.
    CannotMakeChange {
        owed: Cents,
    },
}

impl fmt::Display for VendError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Inventory(e) => e.fmt(f),
            Self::InsufficientCredit { price, credit } => {
                write!(f, "price is {price} but credit is only {credit}")
            }
            Self::CannotMakeChange { owed } => {
                write!(f, "cannot return {owed} in change; please use exact change")
            }
        }
    }
}

impl Error for VendError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Inventory(e) => Some(e),
            _ => None,
        }
    }
}

impl From<InventoryError> for VendError {
    fn from(e: InventoryError) -> Self {
        VendError::Inventory(e)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ServiceError {
    WrongPin,
}

impl fmt::Display for ServiceError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::WrongPin => f.write_str("incorrect service PIN"),
        }
    }
}

impl Error for ServiceError {}

/// A failed transition that hands the machine back, unchanged, in its
/// original state.
///
/// Type-state transitions consume `self`. If a fallible transition returned
/// only an error, the caller would lose the machine (and the customer's
/// money with it). Returning the machine inside the error keeps ownership
/// linear: every path out of a transition yields exactly one machine.
pub struct Rejected<M, E> {
    pub machine: M,
    pub error: E,
}

impl<M, E> Rejected<M, E> {
    pub fn into_parts(self) -> (M, E) {
        (self.machine, self.error)
    }
}

// Manual impls so `Rejected` is usable with `?`/`unwrap` without requiring
// the whole machine to be printed.
impl<M, E: fmt::Debug> fmt::Debug for Rejected<M, E> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Rejected")
            .field("error", &self.error)
            .finish_non_exhaustive()
    }
}

impl<M, E: fmt::Display> fmt::Display for Rejected<M, E> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.error.fmt(f)
    }
}

impl<M, E: Error + 'static> Error for Rejected<M, E> {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        Some(&self.error)
    }
}
