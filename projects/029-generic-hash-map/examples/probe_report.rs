//! Prints probe-length histograms so the effect of load factor and hash
//! quality is visible.
//!
//! ```text
//! cargo run --release --example probe_report
//! ```

use std::hash::{BuildHasherDefault, Hasher};

use robin_hood_map::RobinHoodMap;

/// A deliberately weak hasher: identity on integers. Sequential keys land in
/// sequential slots (fine), but keys that are multiples of a power of two all
/// share their low bits and pile up in the same few home slots.
#[derive(Default)]
struct IdentityHasher(u64);

impl Hasher for IdentityHasher {
    fn finish(&self) -> u64 {
        self.0
    }

    fn write(&mut self, bytes: &[u8]) {
        for &byte in bytes {
            self.0 = (self.0 << 8) | u64::from(byte);
        }
    }

    fn write_u64(&mut self, n: u64) {
        self.0 = n;
    }
}

fn main() {
    const ENTRIES: u64 = 100_000;

    println!("== SipHash (default), {ENTRIES} sequential keys ==");
    let good: RobinHoodMap<u64, ()> = (0..ENTRIES).map(|k| (k, ())).collect();
    print!("{}", good.probe_stats());

    println!("\n== SipHash, filled to exactly the 7/8 load limit ==");
    let mut full = RobinHoodMap::with_capacity(114_688);
    let target = full.capacity() as u64;
    full.extend((0..target).map(|k| (k, ())));
    print!("{}", full.probe_stats());

    println!("\n== Identity hasher, keys that are multiples of 64 (2,000 keys) ==");
    let mut weak = RobinHoodMap::with_hasher(BuildHasherDefault::<IdentityHasher>::default());
    weak.extend((0..2_000u64).map(|k| (k * 64, ())));
    let stats = weak.probe_stats();
    println!(
        "entries={} buckets={} mean_distance={:.1} max_distance={}",
        stats.entries, stats.buckets, stats.mean_distance, stats.max_distance
    );
    println!("(every key's low 6 bits are zero, so only 1 in 64 slots is ever a home slot)");
}
