//! The type-state vending machine.
//!
//! `VendingMachine<S>` carries its current state in the type parameter `S`.
//! Each state exposes only the operations that make sense in it, and every
//! transition consumes the machine and returns it in its next state. The
//! compiler therefore rejects illegal sequences outright:
//!
//! ```text
//!            insert(coin)                select(slot) ok
//!   Idle ────────────────▶ Paying ─────────────────────▶ Dispensing
//!    ▲  ▲                  │  ▲ │ insert(coin)              │
//!    │  │      cancel()    │  └─┘                           │ collect()
//!    │  └──────────────────┘   select(slot) err ⇒ Paying    │
//!    │  └───────────────────────────────────────────────────┘
//!    │ exit()          service(pin)
//!   Maintenance ◀──────────────── Idle
//! ```
//!
//! # Illegal transitions do not compile
//!
//! Selecting a product before paying: `select` does not exist on `Idle`.
//!
//! ```compile_fail,E0599
//! use vending::{VendingMachine, MachineConfig};
//! let m = VendingMachine::new(MachineConfig::default());
//! let _ = m.select("A1".parse().unwrap());
//! ```
//!
//! Restocking while a customer has money in the machine: `restock` exists
//! only in `Maintenance`.
//!
//! ```compile_fail,E0599
//! use vending::{VendingMachine, MachineConfig, Coin};
//! let m = VendingMachine::new(MachineConfig::default()).insert(Coin::Quarter);
//! let _ = m.restock("A1".parse().unwrap(), 1);
//! ```
//!
//! Collecting the same vend twice: `collect` consumes the machine, so the
//! old handle is gone.
//!
//! ```compile_fail,E0382
//! # use vending::{VendingMachine, MachineConfig, Coin, Product, Cents};
//! # let mut svc = VendingMachine::new(MachineConfig::default()).service(MachineConfig::default().pin).unwrap();
//! # svc.load("A1".parse().unwrap(), Product::new("Gum", Cents(25)), 2).unwrap();
//! let dispensing = svc.exit().insert(Coin::Quarter).select("A1".parse().unwrap()).unwrap();
//! let _first = dispensing.collect();
//! let _second = dispensing.collect();
//! ```
//!
//! Forging a machine in an arbitrary state: the fields are private.
//!
//! ```compile_fail,E0451
//! use vending::machine::{VendingMachine, Maintenance};
//! let _ = VendingMachine::<Maintenance> { core: todo!(), state: Maintenance };
//! ```
//!
//! Inventing a new state: `State` is sealed.
//!
//! ```compile_fail,E0277
//! struct Hacked;
//! impl vending::machine::State for Hacked {}
//! ```
//!
//! # The legal sequence does compile
//!
//! ```
//! use vending::{Cents, Coin, MachineConfig, Product, VendingMachine};
//! let config = MachineConfig::default();
//! let pin = config.pin;
//! let mut svc = VendingMachine::new(config).service(pin).unwrap();
//! svc.load("A1".parse().unwrap(), Product::new("Gum", Cents(25)), 2).unwrap();
//! let dispensing = svc.exit().insert(Coin::Quarter).select("A1".parse().unwrap()).unwrap();
//! let (_idle, product, change) = dispensing.collect();
//! assert_eq!(product.name, "Gum");
//! assert!(change.is_empty());
//! ```

use crate::coins::CoinBag;
use crate::error::{InventoryError, Rejected, ServiceError, VendError};
use crate::inventory::{Inventory, Product, SlotId};
use crate::money::{Cents, Coin};

mod sealed {
    pub trait Sealed {}
}

/// Marker trait for machine states. Sealed: only this module can add states,
/// so outside code cannot invent a state with its own transitions.
pub trait State: sealed::Sealed {}

/// Waiting for a customer.
#[derive(Debug)]
pub struct Idle;

/// A customer has inserted coins, held in escrow until a vend or a cancel.
#[derive(Debug)]
pub struct Paying {
    escrow: CoinBag,
}

/// A product has dropped and change is in the tray, waiting to be collected.
#[derive(Debug)]
pub struct Dispensing {
    product: Product,
    change: CoinBag,
}

/// The front panel is open for an operator.
#[derive(Debug)]
pub struct Maintenance;

impl sealed::Sealed for Idle {}
impl sealed::Sealed for Paying {}
impl sealed::Sealed for Dispensing {}
impl sealed::Sealed for Maintenance {}
impl State for Idle {}
impl State for Paying {}
impl State for Dispensing {}
impl State for Maintenance {}

/// Everything needed to construct a machine.
#[derive(Debug, Clone)]
pub struct MachineConfig {
    /// Maximum items per slot.
    pub slot_capacity: u32,
    /// PIN that opens the service panel.
    pub pin: u32,
    /// Coins pre-loaded in the cash box so the machine can give change.
    pub float: CoinBag,
}

impl Default for MachineConfig {
    fn default() -> Self {
        MachineConfig {
            slot_capacity: 10,
            pin: 1234,
            float: CoinBag::from_counts(&[
                (Coin::Quarter, 8),
                (Coin::Dime, 10),
                (Coin::Nickel, 10),
            ]),
        }
    }
}

/// A record of one completed sale.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Sale {
    pub slot: SlotId,
    pub product: String,
    pub price: Cents,
}

/// Data that persists across every state.
#[derive(Debug)]
struct Core {
    inventory: Inventory,
    cash_box: CoinBag,
    pin: u32,
    sales: Vec<Sale>,
}

/// A vending machine in state `S`.
#[derive(Debug)]
pub struct VendingMachine<S: State> {
    core: Core,
    state: S,
}

impl<S: State> VendingMachine<S> {
    /// Moves the shared core into a new state. This is the only way states
    /// change, and it is private to this module.
    fn into_state<T: State>(self, state: T) -> VendingMachine<T> {
        VendingMachine {
            core: self.core,
            state,
        }
    }

    pub fn inventory(&self) -> &Inventory {
        &self.core.inventory
    }

    pub fn sales(&self) -> &[Sale] {
        &self.core.sales
    }

    pub fn revenue(&self) -> Cents {
        self.core
            .sales
            .iter()
            .fold(Cents::ZERO, |acc, s| acc + s.price)
    }

    /// Money in the cash box (excluding any customer escrow).
    pub fn cash_on_hand(&self) -> Cents {
        self.core.cash_box.total()
    }
}

impl VendingMachine<Idle> {
    /// A new, empty machine. Machines always start idle: there is no
    /// constructor for any other state.
    pub fn new(config: MachineConfig) -> Self {
        VendingMachine {
            core: Core {
                inventory: Inventory::new(config.slot_capacity),
                cash_box: config.float,
                pin: config.pin,
                sales: Vec::new(),
            },
            state: Idle,
        }
    }

    /// First coin from a customer.
    pub fn insert(self, coin: Coin) -> VendingMachine<Paying> {
        let mut escrow = CoinBag::new();
        escrow.add(coin);
        self.into_state(Paying { escrow })
    }

    /// Opens the service panel. A wrong PIN leaves the machine idle.
    pub fn service(
        self,
        pin: u32,
    ) -> Result<VendingMachine<Maintenance>, Rejected<Self, ServiceError>> {
        if pin == self.core.pin {
            Ok(self.into_state(Maintenance))
        } else {
            Err(Rejected {
                machine: self,
                error: ServiceError::WrongPin,
            })
        }
    }
}

impl VendingMachine<Paying> {
    pub fn credit(&self) -> Cents {
        self.state.escrow.total()
    }

    pub fn insert(mut self, coin: Coin) -> Self {
        self.state.escrow.add(coin);
        self
    }

    /// Returns the customer's exact coins and goes back to idle.
    pub fn cancel(self) -> (VendingMachine<Idle>, CoinBag) {
        let VendingMachine { core, state } = self;
        (VendingMachine { core, state: Idle }, state.escrow)
    }

    /// Attempts to vend from `slot`.
    ///
    /// Every check runs before anything is mutated, so on failure the
    /// machine comes back exactly as it was, still holding the credit; the
    /// customer can add coins, pick another slot or cancel.
    pub fn select(
        self,
        slot: SlotId,
    ) -> Result<VendingMachine<Dispensing>, Rejected<Self, VendError>> {
        match self.check_vend(slot) {
            Ok(owed) => Ok(self.commit_vend(slot, owed)),
            Err(error) => Err(Rejected {
                machine: self,
                error,
            }),
        }
    }

    /// Pure validation: returns the change owed if the vend can succeed.
    fn check_vend(&self, slot: SlotId) -> Result<Cents, VendError> {
        let item = self.core.inventory.get(slot)?;
        if item.quantity == 0 {
            return Err(InventoryError::SoldOut(slot).into());
        }
        let price = item.product.price;
        let credit = self.credit();
        let owed = credit
            .checked_sub(price)
            .ok_or(VendError::InsufficientCredit { price, credit })?;

        // Change may be paid from the customer's own coins as well as the
        // float, so check against both combined.
        let mut pool = self.core.cash_box.clone();
        pool.absorb(self.state.escrow.clone());
        if pool.can_make_change(owed) {
            Ok(owed)
        } else {
            Err(VendError::CannotMakeChange { owed })
        }
    }

    fn commit_vend(self, slot: SlotId, owed: Cents) -> VendingMachine<Dispensing> {
        let VendingMachine { mut core, state } = self;
        core.cash_box.absorb(state.escrow);
        let change = core
            .cash_box
            .make_change(owed)
            .expect("change feasibility verified in check_vend");
        let product = core
            .inventory
            .take_one(slot)
            .expect("stock verified in check_vend");
        core.sales.push(Sale {
            slot,
            product: product.name.clone(),
            price: product.price,
        });
        VendingMachine {
            core,
            state: Dispensing { product, change },
        }
    }
}

impl VendingMachine<Dispensing> {
    pub fn product(&self) -> &Product {
        &self.state.product
    }

    pub fn change(&self) -> &CoinBag {
        &self.state.change
    }

    /// The customer takes the product and change; the machine is idle again.
    pub fn collect(self) -> (VendingMachine<Idle>, Product, CoinBag) {
        let VendingMachine { core, state } = self;
        (
            VendingMachine { core, state: Idle },
            state.product,
            state.change,
        )
    }
}

impl VendingMachine<Maintenance> {
    pub fn load(
        &mut self,
        slot: SlotId,
        product: Product,
        quantity: u32,
    ) -> Result<(), InventoryError> {
        self.core.inventory.load(slot, product, quantity)
    }

    /// Returns the slot's new quantity.
    pub fn restock(&mut self, slot: SlotId, extra: u32) -> Result<u32, InventoryError> {
        self.core.inventory.restock(slot, extra)
    }

    pub fn set_price(&mut self, slot: SlotId, price: Cents) -> Result<(), InventoryError> {
        self.core.inventory.set_price(slot, price)
    }

    pub fn add_float(&mut self, coin: Coin, count: u32) {
        self.core.cash_box.add_many(coin, count);
    }

    /// Empties the cash box.
    pub fn withdraw_cash(&mut self) -> CoinBag {
        std::mem::take(&mut self.core.cash_box)
    }

    pub fn exit(self) -> VendingMachine<Idle> {
        self.into_state(Idle)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn slot(s: &str) -> SlotId {
        s.parse().unwrap()
    }

    fn stocked(float: CoinBag) -> VendingMachine<Idle> {
        let config = MachineConfig {
            float,
            ..MachineConfig::default()
        };
        let pin = config.pin;
        let mut svc = VendingMachine::new(config).service(pin).unwrap();
        svc.load(slot("A1"), Product::new("Cola", Cents(125)), 2)
            .unwrap();
        svc.load(slot("B2"), Product::new("Chips", Cents(65)), 0)
            .unwrap();
        svc.exit()
    }

    #[test]
    fn exact_payment_vends_without_change() {
        let m = stocked(CoinBag::new())
            .insert(Coin::Dollar)
            .insert(Coin::Quarter);
        let (idle, product, change) = m.select(slot("A1")).unwrap().collect();
        assert_eq!(product.name, "Cola");
        assert!(change.is_empty());
        assert_eq!(idle.inventory().get(slot("A1")).unwrap().quantity, 1);
        assert_eq!(idle.revenue(), Cents(125));
        assert_eq!(idle.cash_on_hand(), Cents(125));
    }

    #[test]
    fn overpayment_returns_change_from_float() {
        let float = CoinBag::from_counts(&[(Coin::Quarter, 4)]);
        let m = stocked(float).insert(Coin::Dollar).insert(Coin::Dollar);
        let d = m.select(slot("A1")).unwrap();
        assert_eq!(d.change().total(), Cents(75));
        let (idle, _, _) = d.collect();
        // 100 float + 200 paid - 75 change
        assert_eq!(idle.cash_on_hand(), Cents(225));
    }

    #[test]
    fn insufficient_credit_keeps_escrow() {
        let m = stocked(CoinBag::new()).insert(Coin::Dollar);
        let (m, err) = m.select(slot("A1")).unwrap_err().into_parts();
        assert_eq!(
            err,
            VendError::InsufficientCredit {
                price: Cents(125),
                credit: Cents(100)
            }
        );
        assert_eq!(m.credit(), Cents(100));
        // The customer tops up and succeeds.
        assert!(m.insert(Coin::Quarter).select(slot("A1")).is_ok());
    }

    #[test]
    fn sold_out_and_unknown_slots_are_rejected() {
        let m = stocked(CoinBag::new()).insert(Coin::Dollar);
        let (m, err) = m.select(slot("B2")).unwrap_err().into_parts();
        assert_eq!(
            err,
            VendError::Inventory(InventoryError::SoldOut(slot("B2")))
        );
        let (_, err) = m.select(slot("Z9")).unwrap_err().into_parts();
        assert_eq!(
            err,
            VendError::Inventory(InventoryError::UnknownSlot(slot("Z9")))
        );
    }

    #[test]
    fn refuses_vend_it_cannot_make_change_for() {
        let m = stocked(CoinBag::new())
            .insert(Coin::Dollar)
            .insert(Coin::Dollar);
        let rejected = m.select(slot("A1")).unwrap_err();
        assert_eq!(
            rejected.error,
            VendError::CannotMakeChange { owed: Cents(75) }
        );
        // Nothing was sold or moved.
        let (idle, refund) = rejected.machine.cancel();
        assert_eq!(refund, CoinBag::from_counts(&[(Coin::Dollar, 2)]));
        assert!(idle.sales().is_empty());
        assert_eq!(idle.inventory().get(slot("A1")).unwrap().quantity, 2);
    }

    #[test]
    fn change_can_come_from_customer_coins() {
        // Empty float: six quarters for a $1.25 item. The 25¢ change can
        // only come from the customer's own escrowed coins.
        let mut m = stocked(CoinBag::new()).insert(Coin::Quarter);
        for _ in 0..5 {
            m = m.insert(Coin::Quarter);
        }
        let d = m.select(slot("A1")).unwrap();
        assert_eq!(d.change(), &CoinBag::from_counts(&[(Coin::Quarter, 1)]));
    }

    #[test]
    fn cancel_returns_the_same_coins() {
        let m = stocked(CoinBag::new())
            .insert(Coin::Dime)
            .insert(Coin::Nickel);
        let (idle, refund) = m.cancel();
        assert_eq!(
            refund,
            CoinBag::from_counts(&[(Coin::Dime, 1), (Coin::Nickel, 1)])
        );
        assert_eq!(idle.cash_on_hand(), Cents::ZERO);
    }

    #[test]
    fn wrong_pin_leaves_machine_idle() {
        let m = stocked(CoinBag::new());
        let (m, err) = m.service(0).unwrap_err().into_parts();
        assert_eq!(err, ServiceError::WrongPin);
        // Still usable as an idle machine.
        let _paying = m.insert(Coin::Dime);
    }

    #[test]
    fn maintenance_operations() {
        let m = stocked(CoinBag::new())
            .insert(Coin::Dollar)
            .insert(Coin::Quarter);
        let (idle, _, _) = m.select(slot("A1")).unwrap().collect();
        let mut svc = idle.service(1234).unwrap();
        assert_eq!(svc.restock(slot("A1"), 3), Ok(4));
        svc.set_price(slot("A1"), Cents(150)).unwrap();
        svc.add_float(Coin::Dime, 5);
        let cash = svc.withdraw_cash();
        assert_eq!(cash.total(), Cents(175));
        let idle = svc.exit();
        assert_eq!(idle.cash_on_hand(), Cents::ZERO);
        assert_eq!(
            idle.inventory().get(slot("A1")).unwrap().product.price,
            Cents(150)
        );
        // Sales history survives maintenance.
        assert_eq!(idle.sales().len(), 1);
    }
}
