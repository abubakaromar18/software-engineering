//! Probe-length statistics, used to observe how well the table is doing.

use std::fmt;

/// A snapshot of how far entries sit from their home slots.
#[derive(Debug, Clone, PartialEq)]
pub struct ProbeStats {
    /// Number of entries.
    pub entries: usize,
    /// Number of slots in the bucket array.
    pub buckets: usize,
    /// Longest probe distance of any entry. A successful lookup never
    /// probes more than `max_distance + 1` slots.
    pub max_distance: usize,
    /// Mean probe distance over all entries.
    pub mean_distance: f64,
    /// `histogram[d]` is the number of entries at probe distance `d`.
    pub histogram: Vec<usize>,
}

impl ProbeStats {
    pub(crate) fn from_distances<I>(distances: I, buckets: usize) -> Self
    where
        I: IntoIterator<Item = usize>,
    {
        let mut histogram = Vec::new();
        let mut entries = 0;
        let mut total = 0;
        for distance in distances {
            if histogram.len() <= distance {
                histogram.resize(distance + 1, 0);
            }
            histogram[distance] += 1;
            entries += 1;
            total += distance;
        }
        Self {
            entries,
            buckets,
            max_distance: histogram.len().saturating_sub(1),
            mean_distance: if entries == 0 {
                0.0
            } else {
                total as f64 / entries as f64
            },
            histogram,
        }
    }

    /// Fraction of slots that are occupied.
    pub fn load_factor(&self) -> f64 {
        if self.buckets == 0 {
            0.0
        } else {
            self.entries as f64 / self.buckets as f64
        }
    }
}

impl fmt::Display for ProbeStats {
    /// A short report with a text histogram, one row per probe distance.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(
            f,
            "entries={} buckets={} load={:.3} mean_distance={:.3} max_distance={}",
            self.entries,
            self.buckets,
            self.load_factor(),
            self.mean_distance,
            self.max_distance
        )?;
        const BAR_WIDTH: usize = 40;
        let tallest = self.histogram.iter().copied().max().unwrap_or(0).max(1);
        for (distance, &count) in self.histogram.iter().enumerate() {
            let bar = "#".repeat(count * BAR_WIDTH / tallest);
            writeln!(f, "  d={distance:<3} {count:>8} {bar}")?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn summarises_distances() {
        let stats = ProbeStats::from_distances([0, 0, 1, 3], 8);
        assert_eq!(stats.entries, 4);
        assert_eq!(stats.max_distance, 3);
        assert_eq!(stats.histogram, vec![2, 1, 0, 1]);
        assert!((stats.mean_distance - 1.0).abs() < f64::EPSILON);
        assert!((stats.load_factor() - 0.5).abs() < f64::EPSILON);
    }

    #[test]
    fn empty_table_has_zeroed_stats() {
        let stats = ProbeStats::from_distances(std::iter::empty(), 0);
        assert_eq!(stats.max_distance, 0);
        assert_eq!(stats.mean_distance, 0.0);
        assert_eq!(stats.load_factor(), 0.0);
        assert!(stats.to_string().starts_with("entries=0"));
    }
}
