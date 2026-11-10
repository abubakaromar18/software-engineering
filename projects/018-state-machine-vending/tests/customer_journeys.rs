//! End-to-end journeys through the public typed API.

use vending::machine::Idle;
use vending::{
    Cents, Coin, CoinBag, InventoryError, MachineConfig, Product, SlotId, VendError, VendingMachine,
};

fn slot(s: &str) -> SlotId {
    s.parse().unwrap()
}

fn machine_with(float: CoinBag, stock: &[(&str, &str, u32, u32)]) -> VendingMachine<Idle> {
    let config = MachineConfig {
        float,
        slot_capacity: 5,
        pin: 42,
    };
    let mut svc = VendingMachine::new(config).service(42).unwrap();
    for &(id, name, cents, qty) in stock {
        svc.load(slot(id), Product::new(name, Cents(cents)), qty)
            .unwrap();
    }
    svc.exit()
}

#[test]
fn many_customers_drain_a_slot_and_money_is_conserved() {
    let float = CoinBag::from_counts(&[(Coin::Dime, 10), (Coin::Nickel, 10)]);
    let float_total = float.total();
    let mut idle = machine_with(float, &[("A1", "Gum", 35, 3)]);
    let mut paid_out = Cents::ZERO;

    for _ in 0..3 {
        let d = idle
            .insert(Coin::Quarter)
            .insert(Coin::Quarter)
            .select(slot("A1"))
            .unwrap();
        let (next, _, change) = d.collect();
        assert_eq!(change.total(), Cents(15));
        paid_out += change.total();
        idle = next;
    }

    // Fourth customer: sold out, gets their money back via cancel.
    let rejected = idle.insert(Coin::Dollar).select(slot("A1")).unwrap_err();
    assert_eq!(
        rejected.error,
        VendError::Inventory(InventoryError::SoldOut(slot("A1")))
    );
    let (idle, refund) = rejected.machine.cancel();
    assert_eq!(refund.total(), Cents(100));

    // Cash box = float + money taken in - change given.
    assert_eq!(
        idle.cash_on_hand(),
        (float_total + Cents(3 * 50)).checked_sub(paid_out).unwrap()
    );
    assert_eq!(idle.revenue(), Cents(3 * 35));
    assert_eq!(idle.sales().len(), 3);
}

#[test]
fn exact_change_only_until_float_is_added() {
    let idle = machine_with(CoinBag::new(), &[("A1", "Cola", 125, 2)]);
    let rejected = idle
        .insert(Coin::Dollar)
        .insert(Coin::Dollar)
        .select(slot("A1"))
        .unwrap_err();
    assert_eq!(
        rejected.error,
        VendError::CannotMakeChange { owed: Cents(75) }
    );

    let (idle, _refund) = rejected.machine.cancel();
    let mut svc = idle.service(42).unwrap();
    svc.add_float(Coin::Quarter, 3);
    let d = svc
        .exit()
        .insert(Coin::Dollar)
        .insert(Coin::Dollar)
        .select(slot("A1"))
        .unwrap();
    assert_eq!(d.change(), &CoinBag::from_counts(&[(Coin::Quarter, 3)]));
}

#[test]
fn rejected_errors_work_with_question_mark() {
    fn buy(idle: VendingMachine<Idle>) -> Result<Product, Box<dyn std::error::Error>> {
        let (_, product, _) = idle.insert(Coin::Dime).select("A1".parse()?)?.collect();
        Ok(product)
    }
    let idle = machine_with(CoinBag::new(), &[("A1", "Gum", 35, 1)]);
    let err = buy(idle).unwrap_err();
    assert_eq!(err.to_string(), "price is $0.35 but credit is only $0.10");
}
