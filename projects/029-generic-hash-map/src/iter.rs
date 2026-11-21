//! Iterators over a [`RobinHoodMap`](crate::RobinHoodMap).
//!
//! Every iterator walks the bucket array and skips empty slots. Each one
//! also tracks how many entries remain, so they report exact sizes
//! (`ExactSizeIterator`) and stop scanning as soon as the last entry is
//! returned, without visiting the trailing empty slots.

use std::iter::FusedIterator;
use std::slice;
use std::vec;

use crate::map::Bucket;

/// Borrowing iterator over `(&K, &V)`.
pub struct Iter<'a, K, V> {
    slots: slice::Iter<'a, Option<Bucket<K, V>>>,
    remaining: usize,
}

impl<'a, K, V> Iter<'a, K, V> {
    pub(crate) fn new(slots: &'a [Option<Bucket<K, V>>], len: usize) -> Self {
        Self {
            slots: slots.iter(),
            remaining: len,
        }
    }
}

impl<K, V> Clone for Iter<'_, K, V> {
    fn clone(&self) -> Self {
        Self {
            slots: self.slots.clone(),
            remaining: self.remaining,
        }
    }
}

impl<'a, K, V> Iterator for Iter<'a, K, V> {
    type Item = (&'a K, &'a V);

    fn next(&mut self) -> Option<Self::Item> {
        if self.remaining == 0 {
            return None;
        }
        let bucket = self.slots.by_ref().flatten().next()?;
        self.remaining -= 1;
        Some((&bucket.key, &bucket.value))
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        (self.remaining, Some(self.remaining))
    }
}

impl<K, V> ExactSizeIterator for Iter<'_, K, V> {}
impl<K, V> FusedIterator for Iter<'_, K, V> {}

/// Borrowing iterator over `(&K, &mut V)`.
pub struct IterMut<'a, K, V> {
    slots: slice::IterMut<'a, Option<Bucket<K, V>>>,
    remaining: usize,
}

impl<'a, K, V> IterMut<'a, K, V> {
    pub(crate) fn new(slots: &'a mut [Option<Bucket<K, V>>], len: usize) -> Self {
        Self {
            slots: slots.iter_mut(),
            remaining: len,
        }
    }
}

impl<'a, K, V> Iterator for IterMut<'a, K, V> {
    type Item = (&'a K, &'a mut V);

    fn next(&mut self) -> Option<Self::Item> {
        if self.remaining == 0 {
            return None;
        }
        let bucket = self.slots.by_ref().flatten().next()?;
        self.remaining -= 1;
        Some((&bucket.key, &mut bucket.value))
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        (self.remaining, Some(self.remaining))
    }
}

impl<K, V> ExactSizeIterator for IterMut<'_, K, V> {}
impl<K, V> FusedIterator for IterMut<'_, K, V> {}

/// Owning iterator over `(K, V)`.
pub struct IntoIter<K, V> {
    slots: vec::IntoIter<Option<Bucket<K, V>>>,
    remaining: usize,
}

impl<K, V> IntoIter<K, V> {
    pub(crate) fn new(slots: Vec<Option<Bucket<K, V>>>, len: usize) -> Self {
        Self {
            slots: slots.into_iter(),
            remaining: len,
        }
    }
}

impl<K, V> Iterator for IntoIter<K, V> {
    type Item = (K, V);

    fn next(&mut self) -> Option<Self::Item> {
        if self.remaining == 0 {
            return None;
        }
        let bucket = self.slots.by_ref().flatten().next()?;
        self.remaining -= 1;
        Some((bucket.key, bucket.value))
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        (self.remaining, Some(self.remaining))
    }
}

impl<K, V> ExactSizeIterator for IntoIter<K, V> {}
impl<K, V> FusedIterator for IntoIter<K, V> {}

/// Iterator over the keys of a map.
pub struct Keys<'a, K, V> {
    pub(crate) inner: Iter<'a, K, V>,
}

impl<'a, K, V> Iterator for Keys<'a, K, V> {
    type Item = &'a K;

    fn next(&mut self) -> Option<&'a K> {
        self.inner.next().map(|(key, _)| key)
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.inner.size_hint()
    }
}

impl<K, V> ExactSizeIterator for Keys<'_, K, V> {}
impl<K, V> FusedIterator for Keys<'_, K, V> {}

/// Iterator over the values of a map.
pub struct Values<'a, K, V> {
    pub(crate) inner: Iter<'a, K, V>,
}

impl<'a, K, V> Iterator for Values<'a, K, V> {
    type Item = &'a V;

    fn next(&mut self) -> Option<&'a V> {
        self.inner.next().map(|(_, value)| value)
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.inner.size_hint()
    }
}

impl<K, V> ExactSizeIterator for Values<'_, K, V> {}
impl<K, V> FusedIterator for Values<'_, K, V> {}

/// Iterator over mutable references to the values of a map.
pub struct ValuesMut<'a, K, V> {
    pub(crate) inner: IterMut<'a, K, V>,
}

impl<'a, K, V> Iterator for ValuesMut<'a, K, V> {
    type Item = &'a mut V;

    fn next(&mut self) -> Option<&'a mut V> {
        self.inner.next().map(|(_, value)| value)
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.inner.size_hint()
    }
}

impl<K, V> ExactSizeIterator for ValuesMut<'_, K, V> {}
impl<K, V> FusedIterator for ValuesMut<'_, K, V> {}
