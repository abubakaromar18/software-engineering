// binary_heap.hpp — a value-semantic binary heap / priority queue.
//
// Compared with std::priority_queue this adds: O(n) construction from a range,
// a non-throwing `try_pop()` that returns the element (std::priority_queue's
// pop() returns void, forcing a copy out of top()), move-only element support
// for `pop()`, `reserve()`, and checked access that throws on an empty heap.
#pragma once

#include <concepts>
#include <cstddef>
#include <functional>
#include <initializer_list>
#include <iterator>
#include <optional>
#include <utility>
#include <vector>

#include "heapq/errors.hpp"
#include "heapq/heap_algorithms.hpp"

namespace heapq {

/// A binary heap. The element for which `Compare` says "comes before every
/// other element" is on top; with the default std::less that is the minimum.
template <class T, class Compare = std::less<T>>
    requires std::strict_weak_order<Compare&, const T&, const T&>
class BinaryHeap {
public:
    using value_type = T;
    using size_type = std::size_t;
    using value_compare = Compare;
    using const_iterator = typename std::vector<T>::const_iterator;

    BinaryHeap() = default;
    explicit BinaryHeap(Compare compare) : compare_(std::move(compare)) {}

    /// Builds a heap from a range in O(n) using Floyd's algorithm.
    template <std::input_iterator It, std::sentinel_for<It> S>
    BinaryHeap(It first, S last, Compare compare = Compare{})
        : data_(first, last), compare_(std::move(compare)) {
        heapq::make_heap(data_.begin(), data_.size(), compare_, slot_swapper(data_.begin()));
    }

    BinaryHeap(std::initializer_list<T> init, Compare compare = Compare{})
        : BinaryHeap(init.begin(), init.end(), std::move(compare)) {}

    [[nodiscard]] size_type size() const noexcept { return data_.size(); }
    [[nodiscard]] bool empty() const noexcept { return data_.empty(); }
    void reserve(size_type capacity) { data_.reserve(capacity); }
    void clear() noexcept { data_.clear(); }

    /// The element that pop() would return next. Throws EmptyHeapError.
    [[nodiscard]] const T& top() const {
        if (empty()) throw EmptyHeapError{};
        return data_.front();
    }

    void push(const T& value) { emplace(value); }
    void push(T&& value) { emplace(std::move(value)); }

    template <class... Args>
    void emplace(Args&&... args) {
        data_.emplace_back(std::forward<Args>(args)...);
        sift_up(data_.begin(), data_.size() - 1, compare_, slot_swapper(data_.begin()));
    }

    /// Removes and returns the top element. Throws EmptyHeapError.
    T pop() {
        if (empty()) throw EmptyHeapError{};
        return remove_top();
    }

    /// Removes and returns the top element, or std::nullopt when empty.
    [[nodiscard]] std::optional<T> try_pop() {
        if (empty()) return std::nullopt;
        return remove_top();
    }

    /// Read-only view of the underlying array, in heap (not sorted) order.
    /// Useful for inspection and for iterating without consuming the heap.
    [[nodiscard]] const_iterator begin() const noexcept { return data_.begin(); }
    [[nodiscard]] const_iterator end() const noexcept { return data_.end(); }

    [[nodiscard]] const Compare& compare() const noexcept { return compare_; }

private:
    // Precondition: !empty(). Moves the last leaf into the root's slot and
    // restores the heap property with a single sift-down.
    T remove_top() {
        std::iter_swap(data_.begin(), std::prev(data_.end()));
        T result = std::move(data_.back());
        data_.pop_back();
        sift_down(data_.begin(), data_.size(), 0, compare_, slot_swapper(data_.begin()));
        return result;
    }

    std::vector<T> data_;
    [[no_unique_address]] Compare compare_{};
};

/// Convenience alias for a heap whose largest element is on top.
template <class T>
using MaxHeap = BinaryHeap<T, std::greater<T>>;

}  // namespace heapq
