//! Behavioural tests of the public API, written against the documented
//! contract rather than the internals.

use std::cell::Cell;
use std::collections::HashMap;
use std::rc::Rc;

use robin_hood_map::{Entry, RobinHoodMap};

#[test]
fn insert_get_and_overwrite() {
    let mut map = RobinHoodMap::new();
    assert_eq!(map.insert("k", 1), None);
    assert_eq!(map.insert("k", 2), Some(1));
    assert_eq!(map.get("k"), Some(&2));
    assert_eq!(map.len(), 1);
}

#[test]
fn lookups_accept_borrowed_keys() {
    let mut map: RobinHoodMap<String, usize> = RobinHoodMap::new();
    map.insert("alpha".to_string(), 1);
    // &str lookups against String keys, as with std::HashMap.
    assert!(map.contains_key("alpha"));
    assert_eq!(map["alpha"], 1);
    assert_eq!(map.get_key_value("alpha"), Some((&"alpha".to_string(), &1)));
    assert_eq!(map.remove("alpha"), Some(1));
    assert!(map.is_empty());
}

#[test]
fn get_mut_and_values_mut_modify_in_place() {
    let mut map: RobinHoodMap<u32, u32> = (0..10).map(|i| (i, i)).collect();
    *map.get_mut(&3).unwrap() = 300;
    map.values_mut().for_each(|v| *v += 1);
    assert_eq!(map[&3], 301);
    assert_eq!(map[&9], 10);
}

#[test]
#[should_panic(expected = "key not found")]
fn index_panics_on_missing_key() {
    let map: RobinHoodMap<u8, u8> = RobinHoodMap::new();
    let _ = map[&1];
}

#[test]
fn entry_api_counts_words() {
    let text = "the quick brown fox jumps over the lazy dog the end";
    let mut counts = RobinHoodMap::new();
    for word in text.split_whitespace() {
        *counts.entry(word).or_insert(0) += 1;
    }
    assert_eq!(counts["the"], 3);
    assert_eq!(counts["fox"], 1);
    assert_eq!(counts.len(), 9);
}

#[test]
fn entry_variants_and_combinators() {
    let mut map = RobinHoodMap::from([("a", 1)]);

    match map.entry("a") {
        Entry::Occupied(mut entry) => {
            assert_eq!(entry.key(), &"a");
            assert_eq!(entry.insert(10), 1);
            assert_eq!(*entry.get(), 10);
        }
        Entry::Vacant(_) => panic!("expected occupied"),
    }
    match map.entry("b") {
        Entry::Vacant(entry) => assert_eq!(entry.into_key(), "b"),
        Entry::Occupied(_) => panic!("expected vacant"),
    }
    assert!(!map.contains_key("b"), "into_key must not insert");

    map.entry("a").and_modify(|v| *v += 1).or_insert(0);
    map.entry("c").and_modify(|v| *v += 1).or_insert(7);
    assert_eq!(map["a"], 11);
    assert_eq!(map["c"], 7);

    let mut lists: RobinHoodMap<&str, Vec<i32>> = RobinHoodMap::new();
    lists.entry("d").or_default().push(1);
    lists.entry("d").or_default().push(2);
    assert_eq!(lists["d"], vec![1, 2]);

    if let Entry::Occupied(entry) = map.entry("a") {
        assert_eq!(entry.remove_entry(), ("a", 11));
    }
    assert_eq!(map.len(), 1);
}

#[test]
fn or_insert_with_is_lazy() {
    let calls = Cell::new(0);
    let mut map = RobinHoodMap::from([(1, 1)]);
    let make = || {
        calls.set(calls.get() + 1);
        42
    };
    map.entry(1).or_insert_with(make);
    assert_eq!(calls.get(), 0);
    map.entry(2).or_insert_with(make);
    assert_eq!(calls.get(), 1);
}

#[test]
fn vacant_insert_returns_reference_to_the_new_value_during_growth() {
    // Every insertion through the entry API must hand back the right slot,
    // including the ones that trigger a resize and the ones that displace
    // residents.
    let mut map = RobinHoodMap::new();
    for i in 0..2_000u32 {
        let slot = map.entry(i).or_insert(i * 2);
        assert_eq!(*slot, i * 2);
        *slot += 1;
    }
    assert!((0..2_000).all(|i| map[&i] == i * 2 + 1));
}

#[test]
fn iterators_visit_every_entry_exactly_once() {
    let map: RobinHoodMap<u32, u32> = (0..500).map(|i| (i, i * i)).collect();
    let iter = map.iter();
    assert_eq!(iter.len(), 500);

    let mut keys: Vec<_> = map.keys().copied().collect();
    keys.sort_unstable();
    assert_eq!(keys, (0..500).collect::<Vec<_>>());

    let sum: u64 = map.values().map(|&v| u64::from(v)).sum();
    assert_eq!(sum, (0..500u64).map(|i| i * i).sum());

    let mut owned: Vec<_> = map.into_iter().collect();
    owned.sort_unstable();
    assert_eq!(owned[499], (499, 499 * 499));
}

#[test]
fn clear_keeps_capacity_and_drops_values() {
    let tracker = Rc::new(());
    let mut map = RobinHoodMap::new();
    for i in 0..100 {
        map.insert(i, Rc::clone(&tracker));
    }
    let buckets = map.bucket_count();
    assert_eq!(Rc::strong_count(&tracker), 101);
    map.clear();
    assert_eq!(Rc::strong_count(&tracker), 1, "values were not dropped");
    assert_eq!(map.bucket_count(), buckets);
    assert!(map.is_empty());
}

#[test]
fn remove_drops_nothing_extra_and_returns_owned_value() {
    let tracker = Rc::new(());
    let mut map = RobinHoodMap::new();
    map.insert("x", Rc::clone(&tracker));
    let value = map.remove("x").unwrap();
    assert_eq!(Rc::strong_count(&tracker), 2);
    drop(value);
    assert_eq!(Rc::strong_count(&tracker), 1);
}

#[test]
fn with_capacity_avoids_reallocation() {
    let mut map = RobinHoodMap::with_capacity(1_000);
    let buckets = map.bucket_count();
    assert!(map.capacity() >= 1_000);
    for i in 0..1_000 {
        map.insert(i, ());
    }
    assert_eq!(map.bucket_count(), buckets);
}

#[test]
fn equality_ignores_order_capacity_and_history() {
    let a: RobinHoodMap<u32, u32> = (0..50).map(|i| (i, i)).collect();
    let mut b = RobinHoodMap::with_capacity(4_096);
    for i in (0..60).rev() {
        b.insert(i, i);
    }
    b.retain(|k, _| *k < 50);
    assert_eq!(a, b);
    b.insert(0, 99);
    assert_ne!(a, b);
}

#[test]
fn debug_formats_like_a_map() {
    let map = RobinHoodMap::from([(1, "one")]);
    assert_eq!(format!("{map:?}"), r#"{1: "one"}"#);
}

#[test]
fn clone_is_independent() {
    let mut original = RobinHoodMap::from([(1, 1)]);
    let copy = original.clone();
    original.insert(1, 2);
    assert_eq!(copy[&1], 1);
}

#[test]
fn probe_stats_are_small_with_a_good_hasher() {
    let map: RobinHoodMap<u64, ()> = (0..100_000).map(|i| (i, ())).collect();
    let stats = map.probe_stats();
    assert_eq!(stats.entries, 100_000);
    assert_eq!(stats.histogram.iter().sum::<usize>(), 100_000);
    assert!(stats.load_factor() <= 0.875);
    // At ~76% load the mean distance is about 1.6 and the
    // maximum in the low tens; a generous bound keeps the test stable.
    assert!(stats.mean_distance < 3.0, "{stats}");
    assert!(stats.max_distance < 64, "{stats}");
}

#[test]
fn matches_std_for_a_long_random_workload() {
    let mut ours = RobinHoodMap::new();
    let mut theirs = HashMap::new();
    let mut state: u64 = 0xDEAD_BEEF_CAFE_F00D;
    let mut next = || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        state
    };
    for step in 0..50_000u64 {
        let key = next() % 4_096;
        match next() % 4 {
            0 | 1 => assert_eq!(ours.insert(key, step), theirs.insert(key, step)),
            2 => assert_eq!(ours.remove(&key), theirs.remove(&key)),
            _ => assert_eq!(ours.get(&key), theirs.get(&key)),
        }
        assert_eq!(ours.len(), theirs.len());
    }
    let mut a: Vec<_> = ours.into_iter().collect();
    let mut b: Vec<_> = theirs.into_iter().collect();
    a.sort_unstable();
    b.sort_unstable();
    assert_eq!(a, b);
}
