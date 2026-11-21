//! # robin-hood-map
//!
//! A generic, open-addressing hash map built from scratch on Robin Hood
//! hashing, linear probing and backward-shift deletion, with no `unsafe`
//! code.
//!
//! * [`RobinHoodMap`] is the map, with an API modelled on
//!   [`std::collections::HashMap`] (including the entry API, borrowed-key
//!   lookups and a pluggable [`BuildHasher`](std::hash::BuildHasher)).
//! * [`ProbeStats`] reports how far entries sit from their home slots, which
//!   makes the effect of the Robin Hood rule (and of a bad hash function)
//!   visible.
//!
//! See `src/map.rs` for a description of the algorithm and its invariants.

#![forbid(unsafe_code)]
#![warn(missing_docs)]

mod entry;
mod iter;
mod map;
mod stats;

pub use entry::{Entry, OccupiedEntry, VacantEntry};
pub use iter::{IntoIter, Iter, IterMut, Keys, Values, ValuesMut};
pub use map::RobinHoodMap;
pub use stats::ProbeStats;
