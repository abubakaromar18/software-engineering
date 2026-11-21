//! The core [`RobinHoodMap`] type: storage layout, probing, insertion,
//! lookup, deletion and resizing.
//!
//! # Storage layout
//!
//! The table is a flat `Vec<Option<Bucket<K, V>>>` whose length is always
//! zero or a power of two, so the "home" slot of a hash is `hash & mask`
//! and wrapping around the end is `(i + 1) & mask`. Each occupied bucket
//! caches the full 64-bit hash of its key. That costs eight bytes per entry
//! but buys three things:
//!
//! * the probe distance of any resident can be computed without rehashing,
//! * most mismatching keys are rejected by comparing hashes, not keys,
//! * resizing never calls the hasher again.
//!
//! # The Robin Hood invariant
//!
//! The *probe distance* (also called probe sequence length, PSL) of an entry
//! is how far it sits from its home slot. On insertion, whenever the entry
//! being placed is farther from home than the resident it meets, the two
//! swap and the evicted resident continues probing. "Take from the rich,
//! give to the poor": no entry is ever left much worse off than its
//! neighbours, which keeps the variance of probe lengths small.
//!
//! A useful consequence: along any probe sequence, the distance of the
//! residents never jumps up by more than one per step. So a lookup that
//! reaches a resident *closer* to home than the probe has travelled knows
//! the key cannot be further along, and stops early. Misses are cheap.
//!
//! # Deletion
//!
//! Instead of tombstones, removal uses *backward-shift deletion*: after
//! emptying a slot, every following entry that is not at its home slot is
//! moved back by one until an empty slot or an entry at home is reached.
//! The table therefore never fills with dead markers and never needs a
//! cleanup rehash.

use std::borrow::Borrow;
use std::collections::hash_map::RandomState;
use std::fmt;
use std::hash::{BuildHasher, Hash};
use std::mem;
use std::ops::Index;

use crate::entry::{Entry, OccupiedEntry, VacantEntry};
use crate::iter::{IntoIter, Iter, IterMut, Keys, Values, ValuesMut};
use crate::stats::ProbeStats;

/// Smallest non-empty bucket array we allocate.
const MIN_BUCKETS: usize = 8;

/// Maximum load factor, as a fraction. 7/8 is aggressive for open
/// addressing, but Robin Hood hashing keeps probe lengths short enough at
/// this load that the memory saving is worth it.
const MAX_LOAD_NUMERATOR: usize = 7;
const MAX_LOAD_DENOMINATOR: usize = 8;

/// One occupied slot: the cached hash plus the key/value pair.
#[derive(Clone)]
pub(crate) struct Bucket<K, V> {
    pub(crate) hash: u64,
    pub(crate) key: K,
    pub(crate) value: V,
}

/// An open-addressing hash map using Robin Hood hashing with linear probing
/// and backward-shift deletion.
///
/// The API mirrors the commonly used parts of
/// [`std::collections::HashMap`], including the entry API and lookups by any
/// borrowed form of the key.
///
/// ```
/// use robin_hood_map::RobinHoodMap;
///
/// let mut stock = RobinHoodMap::new();
/// stock.insert("apples", 3);
/// stock.insert("pears", 5);
/// *stock.entry("apples").or_insert(0) += 2;
///
/// assert_eq!(stock.get("apples"), Some(&5));
/// assert_eq!(stock.remove("pears"), Some(5));
/// assert_eq!(stock.len(), 1);
/// ```
#[derive(Clone)]
pub struct RobinHoodMap<K, V, S = RandomState> {
    pub(crate) slots: Vec<Option<Bucket<K, V>>>,
    pub(crate) len: usize,
    hash_builder: S,
}

/// Number of buckets needed to hold `entries` without exceeding the maximum
/// load factor. Always zero or a power of two.
fn buckets_for(entries: usize) -> usize {
    if entries == 0 {
        return 0;
    }
    // ceil(entries * 8 / 7), computed without overflowing on large inputs.
    let scaled = entries
        .checked_mul(MAX_LOAD_DENOMINATOR)
        .map(|n| n.div_ceil(MAX_LOAD_NUMERATOR))
        .expect("capacity overflow");
    scaled
        .max(MIN_BUCKETS)
        .checked_next_power_of_two()
        .expect("capacity overflow")
}

/// An empty bucket array of the given size.
fn empty_slots<K, V>(buckets: usize) -> Vec<Option<Bucket<K, V>>> {
    let mut slots = Vec::with_capacity(buckets);
    slots.resize_with(buckets, || None);
    slots
}

impl<K, V> RobinHoodMap<K, V, RandomState> {
    /// Creates an empty map. Does not allocate until the first insertion.
    pub fn new() -> Self {
        Self::with_hasher(RandomState::new())
    }

    /// Creates an empty map that can hold at least `capacity` entries
    /// without reallocating.
    pub fn with_capacity(capacity: usize) -> Self {
        Self::with_capacity_and_hasher(capacity, RandomState::new())
    }
}

impl<K, V, S> RobinHoodMap<K, V, S> {
    /// Creates an empty map that uses `hash_builder` to hash keys.
    pub fn with_hasher(hash_builder: S) -> Self {
        Self::with_capacity_and_hasher(0, hash_builder)
    }

    /// Creates an empty map with room for `capacity` entries, using
    /// `hash_builder` to hash keys.
    pub fn with_capacity_and_hasher(capacity: usize, hash_builder: S) -> Self {
        Self {
            slots: empty_slots(buckets_for(capacity)),
            len: 0,
            hash_builder,
        }
    }

    /// Number of entries in the map.
    pub fn len(&self) -> usize {
        self.len
    }

    /// `true` if the map holds no entries.
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// Number of entries the map can hold before it has to grow.
    pub fn capacity(&self) -> usize {
        self.slots.len() / MAX_LOAD_DENOMINATOR * MAX_LOAD_NUMERATOR
    }

    /// Number of slots in the underlying bucket array.
    pub fn bucket_count(&self) -> usize {
        self.slots.len()
    }

    /// The map's hasher factory.
    pub fn hasher(&self) -> &S {
        &self.hash_builder
    }

    /// Removes every entry but keeps the allocated buckets.
    pub fn clear(&mut self) {
        self.slots.iter_mut().for_each(|slot| *slot = None);
        self.len = 0;
    }

    /// Iterates over `(&K, &V)` pairs in table order (which is arbitrary).
    pub fn iter(&self) -> Iter<'_, K, V> {
        Iter::new(&self.slots, self.len)
    }

    /// Iterates over `(&K, &mut V)` pairs in table order.
    pub fn iter_mut(&mut self) -> IterMut<'_, K, V> {
        IterMut::new(&mut self.slots, self.len)
    }

    /// Iterates over the keys.
    pub fn keys(&self) -> Keys<'_, K, V> {
        Keys { inner: self.iter() }
    }

    /// Iterates over the values.
    pub fn values(&self) -> Values<'_, K, V> {
        Values { inner: self.iter() }
    }

    /// Iterates over mutable references to the values.
    pub fn values_mut(&mut self) -> ValuesMut<'_, K, V> {
        ValuesMut {
            inner: self.iter_mut(),
        }
    }

    /// Probe-length statistics for the current table, useful for seeing the
    /// effect of Robin Hood hashing and of a poor hash function.
    pub fn probe_stats(&self) -> ProbeStats {
        let distances = self.slots.iter().enumerate().filter_map(|(index, slot)| {
            slot.as_ref()
                .map(|bucket| self.probe_distance(bucket.hash, index))
        });
        ProbeStats::from_distances(distances, self.slots.len())
    }

    /// Slot mask; only meaningful while the table is allocated.
    fn mask(&self) -> usize {
        self.slots.len() - 1
    }

    /// The slot a hash would occupy if there were no collisions.
    fn home_slot(&self, hash: u64) -> usize {
        // Truncating the hash is intentional: only the low bits select the
        // slot. A good hasher (the default SipHash) mixes them well.
        (hash as usize) & self.mask()
    }

    /// How far slot `index` is from the home slot of `hash`, accounting for
    /// wrap-around.
    pub(crate) fn probe_distance(&self, hash: u64, index: usize) -> usize {
        index.wrapping_sub(self.home_slot(hash)) & self.mask()
    }

    /// Places an entry whose key is known to be absent, assuming there is
    /// room for it. Returns the slot where *this* entry ended up; residents
    /// it displaces may move further along.
    pub(crate) fn insert_new(&mut self, hash: u64, key: K, value: V) -> usize {
        debug_assert!(self.len < self.slots.len(), "insert_new needs room");
        let mask = self.mask();
        let mut carried = Bucket { hash, key, value };
        let mut index = self.home_slot(hash);
        let mut distance = 0;
        // Where the caller's entry lands. It is the first slot we write to:
        // either an empty slot or the first resident we displace.
        let mut landed: Option<usize> = None;

        loop {
            let resident_distance = match &self.slots[index] {
                None => {
                    self.slots[index] = Some(carried);
                    self.len += 1;
                    return landed.unwrap_or(index);
                }
                Some(resident) => self.probe_distance(resident.hash, index),
            };
            if resident_distance < distance {
                // The resident is richer (closer to home) than the entry we
                // carry: it gives up its slot and continues the probe.
                let resident = self.slots[index].as_mut().expect("slot is occupied");
                mem::swap(resident, &mut carried);
                landed.get_or_insert(index);
                distance = resident_distance;
            }
            index = (index + 1) & mask;
            distance += 1;
        }
    }

    /// Removes the entry at `index` and closes the gap with backward-shift
    /// deletion.
    pub(crate) fn remove_at(&mut self, index: usize) -> (K, V) {
        let mask = self.mask();
        let removed = self.slots[index].take().expect("remove_at an empty slot");
        self.len -= 1;

        let mut hole = index;
        loop {
            let next = (hole + 1) & mask;
            let should_shift = match &self.slots[next] {
                Some(bucket) => self.probe_distance(bucket.hash, next) > 0,
                None => false,
            };
            if !should_shift {
                break;
            }
            self.slots[hole] = self.slots[next].take();
            hole = next;
        }
        (removed.key, removed.value)
    }

    /// Moves every entry into a fresh bucket array of `buckets` slots.
    /// Cached hashes mean no key is rehashed.
    fn rebuild(&mut self, buckets: usize) {
        let old = mem::replace(&mut self.slots, empty_slots(buckets));
        self.len = 0;
        for bucket in old.into_iter().flatten() {
            self.insert_new(bucket.hash, bucket.key, bucket.value);
        }
    }

    /// Ensures room for `additional` more entries without reallocating.
    pub fn reserve(&mut self, additional: usize) {
        let needed = self.len.checked_add(additional).expect("capacity overflow");
        if needed > self.capacity() {
            self.rebuild(buckets_for(needed));
        }
    }

    /// Shrinks the bucket array as far as the load factor allows.
    pub fn shrink_to_fit(&mut self) {
        let buckets = buckets_for(self.len);
        if buckets < self.slots.len() {
            self.rebuild(buckets);
        }
    }

    /// Keeps only the entries for which `keep` returns `true`.
    ///
    /// Implemented as a rebuild of the same size rather than in-place
    /// removal: in-place backward shifting would move not-yet-visited
    /// entries behind the cursor. The rebuild is O(buckets) and never
    /// rehashes keys.
    pub fn retain<F>(&mut self, mut keep: F)
    where
        F: FnMut(&K, &mut V) -> bool,
    {
        let buckets = self.slots.len();
        let old = mem::replace(&mut self.slots, empty_slots(buckets));
        self.len = 0;
        for mut bucket in old.into_iter().flatten() {
            if keep(&bucket.key, &mut bucket.value) {
                self.insert_new(bucket.hash, bucket.key, bucket.value);
            }
        }
    }
}

impl<K, V, S> RobinHoodMap<K, V, S>
where
    K: Eq + Hash,
    S: BuildHasher,
{
    fn hash_of<Q>(&self, key: &Q) -> u64
    where
        Q: Hash + ?Sized,
    {
        self.hash_builder.hash_one(key)
    }

    /// Slot holding `key`, if present.
    fn find<Q>(&self, hash: u64, key: &Q) -> Option<usize>
    where
        K: Borrow<Q>,
        Q: Eq + ?Sized,
    {
        if self.len == 0 {
            return None;
        }
        let mask = self.mask();
        let mut index = self.home_slot(hash);
        let mut distance = 0;
        loop {
            let bucket = self.slots[index].as_ref()?;
            if self.probe_distance(bucket.hash, index) < distance {
                // Early exit: had the key been inserted, it would have
                // displaced this richer resident.
                return None;
            }
            if bucket.hash == hash && bucket.key.borrow() == key {
                return Some(index);
            }
            index = (index + 1) & mask;
            distance += 1;
        }
    }

    /// Inserts a key/value pair. Returns the previous value if the key was
    /// already present (the stored key is kept, as in `std`).
    pub fn insert(&mut self, key: K, value: V) -> Option<V> {
        match self.entry(key) {
            Entry::Occupied(mut entry) => Some(entry.insert(value)),
            Entry::Vacant(entry) => {
                entry.insert(value);
                None
            }
        }
    }

    /// Gets the entry for `key` for in-place manipulation.
    ///
    /// Like `std`, this reserves room for one more entry up front, so a
    /// [`VacantEntry`] can insert without resizing and the slot it reports
    /// stays valid.
    pub fn entry(&mut self, key: K) -> Entry<'_, K, V, S> {
        self.reserve(1);
        let hash = self.hash_of(&key);
        match self.find(hash, &key) {
            Some(index) => Entry::Occupied(OccupiedEntry::new(self, index)),
            None => Entry::Vacant(VacantEntry::new(self, hash, key)),
        }
    }

    /// A reference to the value for `key`.
    pub fn get<Q>(&self, key: &Q) -> Option<&V>
    where
        K: Borrow<Q>,
        Q: Hash + Eq + ?Sized,
    {
        self.get_key_value(key).map(|(_, value)| value)
    }

    /// The stored key and its value.
    pub fn get_key_value<Q>(&self, key: &Q) -> Option<(&K, &V)>
    where
        K: Borrow<Q>,
        Q: Hash + Eq + ?Sized,
    {
        let index = self.find(self.hash_of(key), key)?;
        let bucket = self.slots[index].as_ref()?;
        Some((&bucket.key, &bucket.value))
    }

    /// A mutable reference to the value for `key`.
    pub fn get_mut<Q>(&mut self, key: &Q) -> Option<&mut V>
    where
        K: Borrow<Q>,
        Q: Hash + Eq + ?Sized,
    {
        let index = self.find(self.hash_of(key), key)?;
        self.slots[index].as_mut().map(|bucket| &mut bucket.value)
    }

    /// `true` if the map contains `key`.
    pub fn contains_key<Q>(&self, key: &Q) -> bool
    where
        K: Borrow<Q>,
        Q: Hash + Eq + ?Sized,
    {
        self.find(self.hash_of(key), key).is_some()
    }

    /// Removes `key`, returning its value if it was present.
    pub fn remove<Q>(&mut self, key: &Q) -> Option<V>
    where
        K: Borrow<Q>,
        Q: Hash + Eq + ?Sized,
    {
        self.remove_entry(key).map(|(_, value)| value)
    }

    /// Removes `key`, returning the stored key and its value.
    pub fn remove_entry<Q>(&mut self, key: &Q) -> Option<(K, V)>
    where
        K: Borrow<Q>,
        Q: Hash + Eq + ?Sized,
    {
        let index = self.find(self.hash_of(key), key)?;
        Some(self.remove_at(index))
    }
}

impl<K, V, S: Default> Default for RobinHoodMap<K, V, S> {
    fn default() -> Self {
        Self::with_hasher(S::default())
    }
}

impl<K, V, S> fmt::Debug for RobinHoodMap<K, V, S>
where
    K: fmt::Debug,
    V: fmt::Debug,
{
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_map().entries(self.iter()).finish()
    }
}

/// Two maps are equal when they hold the same key/value pairs, regardless
/// of hasher, capacity or table order.
impl<K, V, S> PartialEq for RobinHoodMap<K, V, S>
where
    K: Eq + Hash,
    V: PartialEq,
    S: BuildHasher,
{
    fn eq(&self, other: &Self) -> bool {
        self.len == other.len
            && self
                .iter()
                .all(|(key, value)| other.get(key) == Some(value))
    }
}

impl<K, V, S> Eq for RobinHoodMap<K, V, S>
where
    K: Eq + Hash,
    V: Eq,
    S: BuildHasher,
{
}

impl<K, Q, V, S> Index<&Q> for RobinHoodMap<K, V, S>
where
    K: Eq + Hash + Borrow<Q>,
    Q: Eq + Hash + ?Sized,
    S: BuildHasher,
{
    type Output = V;

    /// # Panics
    ///
    /// Panics if the key is not present.
    fn index(&self, key: &Q) -> &V {
        self.get(key).expect("key not found in RobinHoodMap")
    }
}

impl<K, V, S> Extend<(K, V)> for RobinHoodMap<K, V, S>
where
    K: Eq + Hash,
    S: BuildHasher,
{
    fn extend<I: IntoIterator<Item = (K, V)>>(&mut self, iter: I) {
        let iter = iter.into_iter();
        // Reserve for the lower bound only: duplicates may make the real
        // number of new keys smaller.
        self.reserve(iter.size_hint().0);
        for (key, value) in iter {
            self.insert(key, value);
        }
    }
}

impl<K, V, S> FromIterator<(K, V)> for RobinHoodMap<K, V, S>
where
    K: Eq + Hash,
    S: BuildHasher + Default,
{
    fn from_iter<I: IntoIterator<Item = (K, V)>>(iter: I) -> Self {
        let mut map = Self::default();
        map.extend(iter);
        map
    }
}

impl<K, V, const N: usize> From<[(K, V); N]> for RobinHoodMap<K, V, RandomState>
where
    K: Eq + Hash,
{
    fn from(pairs: [(K, V); N]) -> Self {
        pairs.into_iter().collect()
    }
}

impl<K, V, S> IntoIterator for RobinHoodMap<K, V, S> {
    type Item = (K, V);
    type IntoIter = IntoIter<K, V>;

    fn into_iter(self) -> IntoIter<K, V> {
        IntoIter::new(self.slots, self.len)
    }
}

impl<'a, K, V, S> IntoIterator for &'a RobinHoodMap<K, V, S> {
    type Item = (&'a K, &'a V);
    type IntoIter = Iter<'a, K, V>;

    fn into_iter(self) -> Iter<'a, K, V> {
        self.iter()
    }
}

impl<'a, K, V, S> IntoIterator for &'a mut RobinHoodMap<K, V, S> {
    type Item = (&'a K, &'a mut V);
    type IntoIter = IterMut<'a, K, V>;

    fn into_iter(self) -> IterMut<'a, K, V> {
        self.iter_mut()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::hash::{BuildHasherDefault, Hasher};

    /// Hashes every `u64` key to itself, so tests can choose home slots.
    #[derive(Default)]
    struct IdentityHasher(u64);

    impl Hasher for IdentityHasher {
        fn finish(&self) -> u64 {
            self.0
        }
        fn write(&mut self, _bytes: &[u8]) {
            unimplemented!("IdentityHasher only hashes u64 keys");
        }
        fn write_u64(&mut self, n: u64) {
            self.0 = n;
        }
    }

    type IdentityMap = RobinHoodMap<u64, &'static str, BuildHasherDefault<IdentityHasher>>;

    /// Probe distance of each slot, `None` for empty slots.
    fn layout(map: &IdentityMap) -> Vec<Option<(u64, usize)>> {
        map.slots
            .iter()
            .enumerate()
            .map(|(i, slot)| {
                slot.as_ref()
                    .map(|b| (b.key, map.probe_distance(b.hash, i)))
            })
            .collect()
    }

    #[test]
    fn bucket_sizing_respects_load_factor_and_powers_of_two() {
        assert_eq!(buckets_for(0), 0);
        assert_eq!(buckets_for(1), 8);
        assert_eq!(buckets_for(7), 8);
        assert_eq!(buckets_for(8), 16);
        assert_eq!(buckets_for(14), 16);
        assert_eq!(buckets_for(15), 32);
    }

    #[test]
    fn new_map_does_not_allocate() {
        let map: RobinHoodMap<u8, u8> = RobinHoodMap::new();
        assert_eq!(map.bucket_count(), 0);
        assert_eq!(map.capacity(), 0);
        assert_eq!(map.get(&1), None);
    }

    #[test]
    fn poorer_entry_steals_slot_from_richer_resident() {
        let mut map = IdentityMap::with_capacity_and_hasher(7, Default::default());
        assert_eq!(map.bucket_count(), 8);
        map.insert(0, "a"); // home 0, lands 0
        map.insert(1, "b"); // home 1, lands 1
        map.insert(8, "c"); // home 0: passes slot 0 (d=0) and steals slot 1 from "b"
        assert_eq!(
            layout(&map)[..3],
            [Some((0, 0)), Some((8, 1)), Some((1, 1))],
            "key 8 (distance 1) displaced key 1 (distance 0)"
        );
    }

    #[test]
    fn backward_shift_deletion_pulls_followers_home() {
        let mut map = IdentityMap::with_capacity_and_hasher(7, Default::default());
        for key in [0, 8, 16, 3] {
            map.insert(key, "x");
        }
        // 0, 8 and 16 share home slot 0 and fill slots 0..=2 at distances
        // 0, 1 and 2. Key 3 sits at its own home, slot 3.
        assert_eq!(map.remove(&0), Some("x"));
        let after = layout(&map);
        assert_eq!(after[0], Some((8, 0)));
        assert_eq!(after[1], Some((16, 1)));
        assert_eq!(after[2], None, "the gap moved to the end of the cluster");
        assert_eq!(after[3], Some((3, 0)), "entries at home are never shifted");
    }

    #[test]
    fn probing_wraps_around_the_end_of_the_table() {
        let mut map = IdentityMap::with_capacity_and_hasher(7, Default::default());
        map.insert(7, "end");
        map.insert(15, "wrapped"); // home 7, wraps to slot 0
        assert_eq!(layout(&map)[0], Some((15, 1)));
        assert_eq!(map.get(&15), Some(&"wrapped"));
        assert_eq!(map.remove(&7), Some("end"));
        assert_eq!(
            layout(&map)[7],
            Some((15, 0)),
            "shifted back across the wrap"
        );
    }

    #[test]
    fn miss_inside_a_cluster_returns_none() {
        let mut map = IdentityMap::with_capacity_and_hasher(7, Default::default());
        map.insert(0, "zero"); // slot 0, distance 0
        map.insert(1, "one"); // slot 1, distance 0
                              // Key 8 (home 0) is absent: the probe passes slot 0, then meets key 1
                              // at distance 0 < 1 and stops without scanning to an empty slot.
        assert_eq!(map.get(&8), None);
        assert_eq!(map.remove(&8), None);
        assert_eq!(map.len(), 2);
    }

    #[test]
    fn growth_preserves_entries_without_rehashing() {
        let mut map = IdentityMap::with_hasher(Default::default());
        for key in 0..100 {
            map.insert(key, "v");
        }
        assert_eq!(map.len(), 100);
        assert!(map.bucket_count().is_power_of_two());
        assert!(map.len() <= map.capacity());
        assert!((0..100).all(|k| map.contains_key(&k)));
    }

    /// Checks the structural invariants the algorithm relies on:
    /// * `len` matches the number of occupied slots and fits the load factor,
    /// * every entry's cached hash matches its key,
    /// * the Robin Hood property: an entry at distance `d > 0` is preceded by
    ///   an occupied slot whose entry is at distance `>= d - 1` (no gaps, no
    ///   jumps), which is what makes early-exit lookups correct.
    fn assert_invariants<S: BuildHasher>(map: &RobinHoodMap<u64, u64, S>) {
        let occupied = map.slots.iter().filter(|s| s.is_some()).count();
        assert_eq!(occupied, map.len, "len is out of sync");
        assert!(map.len <= map.capacity(), "load factor exceeded");
        for (index, slot) in map.slots.iter().enumerate() {
            let Some(bucket) = slot else { continue };
            assert_eq!(bucket.hash, map.hash_builder.hash_one(bucket.key));
            let distance = map.probe_distance(bucket.hash, index);
            if distance > 0 {
                let prev_index = (index + map.slots.len() - 1) & map.mask();
                let prev = map.slots[prev_index]
                    .as_ref()
                    .expect("gap inside a probe sequence");
                let prev_distance = map.probe_distance(prev.hash, prev_index);
                assert!(prev_distance + 1 >= distance, "Robin Hood order broken");
            }
        }
    }

    /// Sends every key to one of four hash values: worst-case clustering.
    #[derive(Default)]
    struct FourBucketHasher(u64);

    impl Hasher for FourBucketHasher {
        fn finish(&self) -> u64 {
            self.0 % 4
        }
        fn write(&mut self, _bytes: &[u8]) {
            unimplemented!("FourBucketHasher only hashes u64 keys");
        }
        fn write_u64(&mut self, n: u64) {
            self.0 = n;
        }
    }

    /// Deterministic xorshift64 so failures are reproducible.
    fn xorshift(state: &mut u64) -> u64 {
        *state ^= *state << 13;
        *state ^= *state >> 7;
        *state ^= *state << 17;
        *state
    }

    fn stress<S: BuildHasher>(mut map: RobinHoodMap<u64, u64, S>, key_space: u64, ops: usize) {
        let mut model = std::collections::HashMap::new();
        let mut rng = 0x9E37_79B9_7F4A_7C15;
        for step in 0..ops {
            let key = xorshift(&mut rng) % key_space;
            match xorshift(&mut rng) % 10 {
                0..=5 => assert_eq!(map.insert(key, step as u64), model.insert(key, step as u64)),
                6..=8 => assert_eq!(map.remove(&key), model.remove(&key)),
                _ => {
                    map.retain(|k, _| k % 7 != 0);
                    model.retain(|k, _| k % 7 != 0);
                }
            }
            assert_eq!(map.len(), model.len());
            assert_invariants(&map);
        }
        assert_eq!(map.len(), model.len());
        for (key, value) in &model {
            assert_eq!(map.get(key), Some(value));
        }
    }

    #[test]
    fn invariants_hold_under_random_operations() {
        stress(RobinHoodMap::new(), 500, 5_000);
    }

    #[test]
    fn invariants_hold_with_a_pathological_hasher() {
        stress(
            RobinHoodMap::with_hasher(BuildHasherDefault::<FourBucketHasher>::default()),
            200,
            3_000,
        );
    }

    #[test]
    fn shrink_to_fit_releases_buckets() {
        let mut map: RobinHoodMap<u32, u32> = (0..1000).map(|i| (i, i)).collect();
        map.retain(|k, _| *k < 10);
        let before = map.bucket_count();
        map.shrink_to_fit();
        assert!(map.bucket_count() < before);
        assert_eq!(map.bucket_count(), 16);
        assert!((0..10).all(|k| map[&k] == k));
    }
}
