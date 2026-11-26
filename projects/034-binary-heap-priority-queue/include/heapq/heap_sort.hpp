// heap_sort.hpp — in-place, O(n log n) worst-case, O(1) extra space sort.
//
// Heapsort's selling point over quicksort is its guaranteed worst case and
// constant memory; its weaknesses are poor cache locality (children of i live
// at 2i+1, far away for large i) and instability. std::sort (introsort) falls
// back to heapsort for exactly the worst-case guarantee.
#pragma once

#include <algorithm>
#include <cstddef>
#include <functional>
#include <iterator>
#include <ranges>

#include "heapq/heap_algorithms.hpp"

namespace heapq {

/// Sorts [first, last) into ascending order under `comp`. Not stable.
template <std::random_access_iterator It, class Compare = std::ranges::less>
    requires std::sortable<It, Compare>
constexpr void heap_sort(It first, It last, Compare comp = {}) {
    const auto n = static_cast<std::size_t>(std::distance(first, last));
    if (n < 2) return;

    // Ascending output needs the *largest* element on top, so invert `comp`.
    auto before = [&comp](const auto& a, const auto& b) { return std::invoke(comp, b, a); };
    auto swap = slot_swapper(first);

    heapq::make_heap(first, n, before, swap);
    // Repeatedly move the current maximum to the end of the shrinking heap.
    for (std::size_t end = n - 1; end > 0; --end) {
        swap(0, end);
        sift_down(first, end, 0, before, swap);
    }
}

/// Range overload: heapq::heap_sort(vec), heapq::heap_sort(vec, std::greater{}).
template <std::ranges::random_access_range R, class Compare = std::ranges::less>
    requires std::sortable<std::ranges::iterator_t<R>, Compare>
constexpr void heap_sort(R&& range, Compare comp = {}) {
    heap_sort(std::ranges::begin(range), std::ranges::end(range), std::move(comp));
}

}  // namespace heapq
