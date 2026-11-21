//! The entry API: look a key up once, then read, update, insert or remove
//! without a second probe.

use std::hash::{BuildHasher, Hash};

use crate::map::{Bucket, RobinHoodMap};

/// A view into a single slot of a [`RobinHoodMap`], which is either occupied
/// or vacant. Created by [`RobinHoodMap::entry`].
pub enum Entry<'a, K, V, S> {
    /// The key is present.
    Occupied(OccupiedEntry<'a, K, V, S>),
    /// The key is absent.
    Vacant(VacantEntry<'a, K, V, S>),
}

/// An entry whose key is present. Holds the slot index, which stays valid
/// because the entry has exclusive access to the map.
pub struct OccupiedEntry<'a, K, V, S> {
    map: &'a mut RobinHoodMap<K, V, S>,
    index: usize,
}

/// An entry whose key is absent. Holds the key and its already computed
/// hash so insertion does not hash again.
pub struct VacantEntry<'a, K, V, S> {
    map: &'a mut RobinHoodMap<K, V, S>,
    hash: u64,
    key: K,
}

impl<'a, K, V, S> Entry<'a, K, V, S>
where
    K: Eq + Hash,
    S: BuildHasher,
{
    /// The entry's key.
    pub fn key(&self) -> &K {
        match self {
            Entry::Occupied(entry) => entry.key(),
            Entry::Vacant(entry) => entry.key(),
        }
    }

    /// Returns the value, inserting `default` first if the key is absent.
    pub fn or_insert(self, default: V) -> &'a mut V {
        self.or_insert_with(|| default)
    }

    /// Returns the value, inserting the result of `make` first if the key
    /// is absent. `make` is only called when needed.
    pub fn or_insert_with<F: FnOnce() -> V>(self, make: F) -> &'a mut V {
        match self {
            Entry::Occupied(entry) => entry.into_mut(),
            Entry::Vacant(entry) => entry.insert(make()),
        }
    }

    /// Returns the value, inserting `V::default()` first if absent.
    pub fn or_default(self) -> &'a mut V
    where
        V: Default,
    {
        self.or_insert_with(V::default)
    }

    /// Applies `update` to the value if the key is present.
    pub fn and_modify<F: FnOnce(&mut V)>(mut self, update: F) -> Self {
        if let Entry::Occupied(entry) = &mut self {
            update(entry.get_mut());
        }
        self
    }
}

impl<'a, K, V, S> OccupiedEntry<'a, K, V, S> {
    pub(crate) fn new(map: &'a mut RobinHoodMap<K, V, S>, index: usize) -> Self {
        Self { map, index }
    }

    fn bucket(&self) -> &Bucket<K, V> {
        self.map.slots[self.index]
            .as_ref()
            .expect("occupied entry points at a full slot")
    }

    fn bucket_mut(&mut self) -> &mut Bucket<K, V> {
        self.map.slots[self.index]
            .as_mut()
            .expect("occupied entry points at a full slot")
    }

    /// The stored key.
    pub fn key(&self) -> &K {
        &self.bucket().key
    }

    /// The value.
    pub fn get(&self) -> &V {
        &self.bucket().value
    }

    /// The value, mutably, for the lifetime of the entry.
    pub fn get_mut(&mut self) -> &mut V {
        &mut self.bucket_mut().value
    }

    /// The value, mutably, for the lifetime of the map borrow.
    pub fn into_mut(self) -> &'a mut V {
        &mut self.map.slots[self.index]
            .as_mut()
            .expect("occupied entry points at a full slot")
            .value
    }

    /// Replaces the value, returning the old one.
    pub fn insert(&mut self, value: V) -> V {
        std::mem::replace(self.get_mut(), value)
    }

    /// Removes the entry, returning its value.
    pub fn remove(self) -> V {
        self.remove_entry().1
    }

    /// Removes the entry, returning the stored key and value.
    pub fn remove_entry(self) -> (K, V) {
        self.map.remove_at(self.index)
    }
}

impl<'a, K, V, S> VacantEntry<'a, K, V, S> {
    pub(crate) fn new(map: &'a mut RobinHoodMap<K, V, S>, hash: u64, key: K) -> Self {
        Self { map, hash, key }
    }

    /// The key that would be inserted.
    pub fn key(&self) -> &K {
        &self.key
    }

    /// Gives the key back without inserting.
    pub fn into_key(self) -> K {
        self.key
    }

    /// Inserts the value and returns a reference to it.
    ///
    /// The map reserved room when the entry was created, so this never
    /// resizes and the returned slot index is final.
    pub fn insert(self, value: V) -> &'a mut V {
        let index = self.map.insert_new(self.hash, self.key, value);
        &mut self.map.slots[index]
            .as_mut()
            .expect("insert_new returns the slot it filled")
            .value
    }
}
