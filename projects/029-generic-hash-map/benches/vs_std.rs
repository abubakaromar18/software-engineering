//! Criterion benchmarks comparing `RobinHoodMap` with `std::collections::HashMap`.
//!
//! Both maps use the same hasher (`RandomState`, i.e. SipHash-1-3) so the
//! comparison measures table design, not hash function speed.
//!
//! Run with `cargo bench`; HTML-free text reports go to stdout and raw data
//! to `target/criterion/`.

use std::collections::hash_map::RandomState;
use std::collections::HashMap;
use std::hint::black_box;

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use robin_hood_map::RobinHoodMap;

const SIZES: [u64; 2] = [1_000, 100_000];

/// Deterministic, well-spread keys (a multiplicative scramble of 0..n).
fn keys(n: u64) -> Vec<u64> {
    (0..n)
        .map(|i| i.wrapping_mul(0x9E37_79B9_7F4A_7C15))
        .collect()
}

/// Keys guaranteed absent from `keys(n)`: the scramble is a bijection, so
/// the images of n..2n never collide with those of 0..n.
fn missing_keys(n: u64) -> Vec<u64> {
    (n..2 * n)
        .map(|i| i.wrapping_mul(0x9E37_79B9_7F4A_7C15))
        .collect()
}

fn bench_insert(c: &mut Criterion) {
    let mut group = c.benchmark_group("insert");
    for n in SIZES {
        let keys = keys(n);
        group.throughput(Throughput::Elements(n));
        group.bench_with_input(BenchmarkId::new("robin_hood", n), &keys, |b, keys| {
            b.iter(|| {
                let mut map = RobinHoodMap::with_hasher(RandomState::new());
                for &k in keys {
                    map.insert(k, k);
                }
                black_box(map)
            })
        });
        group.bench_with_input(BenchmarkId::new("std", n), &keys, |b, keys| {
            b.iter(|| {
                let mut map = HashMap::with_hasher(RandomState::new());
                for &k in keys {
                    map.insert(k, k);
                }
                black_box(map)
            })
        });
    }
    group.finish();
}

fn bench_lookup(c: &mut Criterion) {
    for (name, probe) in [
        ("lookup_hit", keys as fn(u64) -> Vec<u64>),
        ("lookup_miss", missing_keys),
    ] {
        let mut group = c.benchmark_group(name);
        for n in SIZES {
            let stored = keys(n);
            let probes = probe(n);
            let ours: RobinHoodMap<u64, u64> = stored.iter().map(|&k| (k, k)).collect();
            let theirs: HashMap<u64, u64> = stored.iter().map(|&k| (k, k)).collect();
            group.throughput(Throughput::Elements(n));
            group.bench_with_input(BenchmarkId::new("robin_hood", n), &probes, |b, probes| {
                b.iter(|| probes.iter().filter(|k| ours.contains_key(*k)).count())
            });
            group.bench_with_input(BenchmarkId::new("std", n), &probes, |b, probes| {
                b.iter(|| probes.iter().filter(|k| theirs.contains_key(*k)).count())
            });
        }
        group.finish();
    }
}

fn bench_remove(c: &mut Criterion) {
    let mut group = c.benchmark_group("insert_then_remove");
    for n in SIZES {
        let keys = keys(n);
        group.throughput(Throughput::Elements(n));
        group.bench_with_input(BenchmarkId::new("robin_hood", n), &keys, |b, keys| {
            b.iter(|| {
                let mut map: RobinHoodMap<u64, u64> = keys.iter().map(|&k| (k, k)).collect();
                for k in keys {
                    map.remove(k);
                }
                black_box(map)
            })
        });
        group.bench_with_input(BenchmarkId::new("std", n), &keys, |b, keys| {
            b.iter(|| {
                let mut map: HashMap<u64, u64> = keys.iter().map(|&k| (k, k)).collect();
                for k in keys {
                    map.remove(k);
                }
                black_box(map)
            })
        });
    }
    group.finish();
}

criterion_group!(benches, bench_insert, bench_lookup, bench_remove);
criterion_main!(benches);
