//! Products and the slots that hold them.

use crate::error::InventoryError;
use crate::money::Cents;
use std::collections::BTreeMap;
use std::fmt;
use std::str::FromStr;

/// A slot label such as `A1`: one row letter (A–Z) and one column digit (1–9).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SlotId {
    row: char,
    col: u8,
}

impl SlotId {
    pub fn new(row: char, col: u8) -> Result<Self, InventoryError> {
        let row = row.to_ascii_uppercase();
        if row.is_ascii_uppercase() && (1..=9).contains(&col) {
            Ok(SlotId { row, col })
        } else {
            Err(InventoryError::InvalidSlotId(format!("{row}{col}")))
        }
    }
}

impl FromStr for SlotId {
    type Err = InventoryError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let mut chars = s.trim().chars();
        match (chars.next(), chars.next(), chars.next()) {
            (Some(row), Some(col), None) if col.is_ascii_digit() => {
                SlotId::new(row, col as u8 - b'0')
            }
            _ => Err(InventoryError::InvalidSlotId(s.to_string())),
        }
    }
}

impl fmt::Display for SlotId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}{}", self.row, self.col)
    }
}

/// Something the machine sells. Handed to the customer on a successful vend.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Product {
    pub name: String,
    pub price: Cents,
}

impl Product {
    pub fn new(name: impl Into<String>, price: Cents) -> Self {
        Product {
            name: name.into(),
            price,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Slot {
    pub product: Product,
    pub quantity: u32,
}

/// The machine's stock. Every slot has the same physical capacity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Inventory {
    slots: BTreeMap<SlotId, Slot>,
    capacity: u32,
}

impl Inventory {
    pub fn new(capacity: u32) -> Self {
        Inventory {
            slots: BTreeMap::new(),
            capacity,
        }
    }

    pub fn capacity(&self) -> u32 {
        self.capacity
    }

    pub fn get(&self, id: SlotId) -> Result<&Slot, InventoryError> {
        self.slots.get(&id).ok_or(InventoryError::UnknownSlot(id))
    }

    pub fn iter(&self) -> impl Iterator<Item = (SlotId, &Slot)> {
        self.slots.iter().map(|(id, slot)| (*id, slot))
    }

    /// Puts `product` in slot `id` (replacing whatever was there) with
    /// `quantity` items.
    pub fn load(
        &mut self,
        id: SlotId,
        product: Product,
        quantity: u32,
    ) -> Result<(), InventoryError> {
        self.check_capacity(id, quantity)?;
        if product.price.0 == 0 || product.price.0 % 5 != 0 {
            return Err(InventoryError::InvalidPrice(product.price));
        }
        self.slots.insert(id, Slot { product, quantity });
        Ok(())
    }

    /// Adds `extra` items to an existing slot.
    pub fn restock(&mut self, id: SlotId, extra: u32) -> Result<u32, InventoryError> {
        let current = self.get(id)?.quantity;
        let new_qty = current.saturating_add(extra);
        self.check_capacity(id, new_qty)?;
        let slot = self
            .slots
            .get_mut(&id)
            .expect("slot existence checked above");
        slot.quantity = new_qty;
        Ok(new_qty)
    }

    pub fn set_price(&mut self, id: SlotId, price: Cents) -> Result<(), InventoryError> {
        if price.0 == 0 || price.0 % 5 != 0 {
            return Err(InventoryError::InvalidPrice(price));
        }
        let slot = self
            .slots
            .get_mut(&id)
            .ok_or(InventoryError::UnknownSlot(id))?;
        slot.product.price = price;
        Ok(())
    }

    /// Removes one item from slot `id`. Callers must have checked stock.
    pub(crate) fn take_one(&mut self, id: SlotId) -> Result<Product, InventoryError> {
        let slot = self
            .slots
            .get_mut(&id)
            .ok_or(InventoryError::UnknownSlot(id))?;
        if slot.quantity == 0 {
            return Err(InventoryError::SoldOut(id));
        }
        slot.quantity -= 1;
        Ok(slot.product.clone())
    }

    fn check_capacity(&self, id: SlotId, quantity: u32) -> Result<(), InventoryError> {
        if quantity > self.capacity {
            Err(InventoryError::OverCapacity {
                slot: id,
                capacity: self.capacity,
            })
        } else {
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn a1() -> SlotId {
        "A1".parse().unwrap()
    }

    #[test]
    fn parses_slot_ids() {
        assert_eq!("b3".parse::<SlotId>().unwrap().to_string(), "B3");
        assert!("A0".parse::<SlotId>().is_err());
        assert!("A10".parse::<SlotId>().is_err());
        assert!("11".parse::<SlotId>().is_err());
        assert!("".parse::<SlotId>().is_err());
    }

    #[test]
    fn load_and_take() {
        let mut inv = Inventory::new(5);
        inv.load(a1(), Product::new("Cola", Cents(125)), 1).unwrap();
        assert_eq!(inv.take_one(a1()).unwrap().name, "Cola");
        assert_eq!(inv.take_one(a1()), Err(InventoryError::SoldOut(a1())));
    }

    #[test]
    fn rejects_over_capacity() {
        let mut inv = Inventory::new(3);
        assert!(matches!(
            inv.load(a1(), Product::new("Cola", Cents(125)), 4),
            Err(InventoryError::OverCapacity { .. })
        ));
        inv.load(a1(), Product::new("Cola", Cents(125)), 2).unwrap();
        assert!(inv.restock(a1(), 2).is_err());
        assert_eq!(inv.restock(a1(), 1), Ok(3));
    }

    #[test]
    fn rejects_unpayable_prices() {
        let mut inv = Inventory::new(3);
        assert_eq!(
            inv.load(a1(), Product::new("Gum", Cents(37)), 1),
            Err(InventoryError::InvalidPrice(Cents(37)))
        );
        inv.load(a1(), Product::new("Gum", Cents(35)), 1).unwrap();
        assert!(inv.set_price(a1(), Cents(0)).is_err());
        inv.set_price(a1(), Cents(40)).unwrap();
        assert_eq!(inv.get(a1()).unwrap().product.price, Cents(40));
    }

    #[test]
    fn unknown_slot_errors() {
        let inv = Inventory::new(3);
        assert_eq!(inv.get(a1()), Err(InventoryError::UnknownSlot(a1())));
    }
}
