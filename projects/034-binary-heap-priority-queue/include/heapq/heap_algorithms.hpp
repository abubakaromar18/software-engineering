// heap_algorithms.hpp — the index arithmetic and sift operations every heap in
// this library is built from.
//
// Conventions used throughout `heapq`:
//   * The heap is an implicit binary tree stored in a contiguous array:
//       parent(i) = (i - 1) / 2,  left(i) = 2i + 1,  right(i) = 2i + 2.
//   * `before(a, b)` returns true when `a` must leave the heap before `b`.
//     With the default `std::less`, the smallest element is on top, so every
//     container here is a *min-heap* unless you pass another comparator.
//   * Sift operations never move elements themselves; they call a `swap(i, j)`
//     callback. Plain heaps pass a callback that swaps array slots, while the
//     indexed heap also updates its key -> position table. One algorithm,
//     two bookkeeping policies, no duplicated loops.
#pragma once

#include <concepts>
#include <cstddef>
#include <functional>
#include <iterator>
#include <utility>

namespace heapq {

namespace detail {

[[nodiscard]] constexpr std::size_t parent(std::size_t i) noexcept { return (i - 1) / 2; }
[[nodiscard]] constexpr std::size_t left_child(std::size_t i) noexcept { return 2 * i + 1; }

/// Iterator offset by an unsigned index, without sign-conversion warnings.
template <std::random_access_iterator It>
[[nodiscard]] constexpr It advance_by(It first, std::size_t i) {
    return first + static_cast<std::iter_difference_t<It>>(i);
}

template <std::random_access_iterator It>
[[nodiscard]] constexpr decltype(auto) at(It first, std::size_t i) {
    return *advance_by(first, i);
}

}  // namespace detail

/// Moves the element at index `i` towards the root until its parent should
/// leave the heap no later than it does. Returns the element's final index.
/// O(log n) comparisons.
template <std::random_access_iterator It, class Before, class Swap>
constexpr std::size_t sift_up(It first, std::size_t i, Before& before, Swap&& swap) {
    while (i > 0) {
        const std::size_t p = detail::parent(i);
        if (!before(detail::at(first, i), detail::at(first, p))) break;
        swap(i, p);
        i = p;
    }
    return i;
}

/// Moves the element at index `i` towards the leaves of a heap holding `n`
/// elements, swapping with the child that should leave first. Returns the
/// element's final index. O(log n) comparisons.
template <std::random_access_iterator It, class Before, class Swap>
constexpr std::size_t sift_down(It first, std::size_t n, std::size_t i, Before& before, Swap&& swap) {
    for (;;) {
        const std::size_t l = detail::left_child(i);
        if (l >= n) break;
        const std::size_t r = l + 1;
        const std::size_t best = (r < n && before(detail::at(first, r), detail::at(first, l))) ? r : l;
        if (!before(detail::at(first, best), detail::at(first, i))) break;
        swap(i, best);
        i = best;
    }
    return i;
}

/// Swap callback for heaps that need no bookkeeping beyond the array itself.
template <std::random_access_iterator It>
[[nodiscard]] constexpr auto slot_swapper(It first) noexcept {
    return [first](std::size_t a, std::size_t b) {
        std::iter_swap(detail::advance_by(first, a), detail::advance_by(first, b));
    };
}

/// Floyd's bottom-up heap construction: sift down every internal node,
/// starting from the last one. O(n) total work, versus O(n log n) for n pushes.
template <std::random_access_iterator It, class Before, class Swap>
constexpr void make_heap(It first, std::size_t n, Before& before, Swap&& swap) {
    for (std::size_t i = n / 2; i-- > 0;) {
        sift_down(first, n, i, before, swap);
    }
}

/// True when [first, last) satisfies the heap property under `before`:
/// no child should leave the heap before its parent.
template <std::random_access_iterator It, class Before = std::less<>>
[[nodiscard]] constexpr bool is_heap(It first, It last, Before before = {}) {
    const auto n = static_cast<std::size_t>(std::distance(first, last));
    for (std::size_t i = 1; i < n; ++i) {
        if (before(detail::at(first, i), detail::at(first, detail::parent(i)))) return false;
    }
    return true;
}

}  // namespace heapq
