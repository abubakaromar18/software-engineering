// indexed_heap.hpp — an addressable priority queue with decrease-key.
//
// A plain binary heap cannot change the priority of an element it holds: it
// has no way to find the element without an O(n) scan. IndexedHeap pairs the
// heap array with a hash table mapping each key to its current array index.
// Every swap during a sift updates both slots' entries in that table, so
// lookups are O(1) and decrease_key / update / erase are O(log n).
//
// This is the structure Dijkstra's and Prim's algorithms assume, and the one
// the task scheduler demo uses to escalate and cancel pending tasks.
#pragma once

#include <concepts>
#include <cstddef>
#include <functional>
#include <optional>
#include <unordered_map>
#include <utility>
#include <vector>

#include "heapq/errors.hpp"
#include "heapq/heap_algorithms.hpp"

namespace heapq {

template <class Key, class Priority, class Compare = std::less<Priority>, class Hash = std::hash<Key>,
          class KeyEqual = std::equal_to<Key>>
    requires std::strict_weak_order<Compare&, const Priority&, const Priority&> &&
             std::copy_constructible<Key>
class IndexedHeap {
public:
    struct Entry {
        Key key;
        Priority priority;
    };

    using key_type = Key;
    using priority_type = Priority;
    using size_type = std::size_t;
    using const_iterator = typename std::vector<Entry>::const_iterator;

    IndexedHeap() = default;
    explicit IndexedHeap(Compare compare) : compare_(std::move(compare)) {}

    [[nodiscard]] size_type size() const noexcept { return heap_.size(); }
    [[nodiscard]] bool empty() const noexcept { return heap_.empty(); }
    [[nodiscard]] bool contains(const Key& key) const { return position_.contains(key); }

    void reserve(size_type capacity) {
        heap_.reserve(capacity);
        position_.reserve(capacity);
    }

    void clear() noexcept {
        heap_.clear();
        position_.clear();
    }

    /// Inserts a new key. Throws DuplicateKeyError if the key is present
    /// (the strong exception guarantee holds: the heap is left unchanged).
    void push(const Key& key, Priority priority) {
        if (contains(key)) throw DuplicateKeyError{};
        heap_.push_back(Entry{key, std::move(priority)});
        const std::size_t index = heap_.size() - 1;
        try {
            position_.emplace(key, index);
        } catch (...) {
            heap_.pop_back();
            throw;
        }
        restore_up(index);
    }

    /// The entry that pop() would return next. Throws EmptyHeapError.
    [[nodiscard]] const Entry& top() const {
        if (empty()) throw EmptyHeapError{};
        return heap_.front();
    }

    /// Removes and returns the top entry. Throws EmptyHeapError.
    Entry pop() {
        if (empty()) throw EmptyHeapError{};
        return remove_at(0);
    }

    [[nodiscard]] std::optional<Entry> try_pop() {
        if (empty()) return std::nullopt;
        return remove_at(0);
    }

    /// The current priority of `key`. Throws MissingKeyError.
    [[nodiscard]] const Priority& priority_of(const Key& key) const { return heap_[index_of(key)].priority; }

    /// Gives `key` a priority that makes it leave the heap no later than
    /// before ("decrease" in min-heap terms). Only sifts up, so it is the
    /// cheaper half of update(). Throws MissingKeyError, or
    /// PriorityDirectionError if the new priority would move the key away
    /// from the top.
    void decrease_key(const Key& key, Priority priority) {
        const std::size_t index = index_of(key);
        if (compare_(heap_[index].priority, priority)) throw PriorityDirectionError{};
        heap_[index].priority = std::move(priority);
        restore_up(index);
    }

    /// Sets any new priority for `key`, sifting in whichever direction is
    /// needed. Throws MissingKeyError.
    void update(const Key& key, Priority priority) {
        const std::size_t index = index_of(key);
        heap_[index].priority = std::move(priority);
        restore(index);
    }

    /// Removes `key` if present. Returns its entry, or nullopt if absent.
    std::optional<Entry> erase(const Key& key) {
        const auto it = position_.find(key);
        if (it == position_.end()) return std::nullopt;
        return remove_at(it->second);
    }

    /// Iterates entries in heap (not priority) order without consuming them.
    [[nodiscard]] const_iterator begin() const noexcept { return heap_.begin(); }
    [[nodiscard]] const_iterator end() const noexcept { return heap_.end(); }

    /// Verifies the heap property and that the position table agrees with
    /// the array. O(n); intended for tests and debug assertions.
    [[nodiscard]] bool check_invariants() const {
        if (position_.size() != heap_.size()) return false;
        for (std::size_t i = 0; i < heap_.size(); ++i) {
            const auto it = position_.find(heap_[i].key);
            if (it == position_.end() || it->second != i) return false;
            if (i > 0 && compare_(heap_[i].priority, heap_[detail::parent(i)].priority)) return false;
        }
        return true;
    }

private:
    [[nodiscard]] std::size_t index_of(const Key& key) const {
        const auto it = position_.find(key);
        if (it == position_.end()) throw MissingKeyError{};
        return it->second;
    }

    // Comparator over entries, as the sift algorithms expect.
    [[nodiscard]] auto entry_before() const {
        return [this](const Entry& a, const Entry& b) { return compare_(a.priority, b.priority); };
    }

    // Swap callback that keeps the position table in sync with the array.
    [[nodiscard]] auto tracking_swapper() {
        return [this](std::size_t a, std::size_t b) {
            std::swap(heap_[a], heap_[b]);
            position_.find(heap_[a].key)->second = a;
            position_.find(heap_[b].key)->second = b;
        };
    }

    void restore_up(std::size_t index) {
        auto before = entry_before();
        sift_up(heap_.begin(), index, before, tracking_swapper());
    }

    // After an arbitrary change at `index`, at most one direction moves it.
    void restore(std::size_t index) {
        auto before = entry_before();
        const std::size_t moved = sift_up(heap_.begin(), index, before, tracking_swapper());
        if (moved == index) sift_down(heap_.begin(), heap_.size(), index, before, tracking_swapper());
    }

    // Swaps the target with the last leaf, detaches it, then repairs the
    // displaced leaf, which may need to move either way when index != 0.
    Entry remove_at(std::size_t index) {
        const std::size_t last = heap_.size() - 1;
        if (index != last) tracking_swapper()(index, last);
        Entry removed = std::move(heap_.back());
        heap_.pop_back();
        position_.erase(removed.key);
        if (index < heap_.size()) restore(index);
        return removed;
    }

    std::vector<Entry> heap_;
    std::unordered_map<Key, std::size_t, Hash, KeyEqual> position_;
    [[no_unique_address]] Compare compare_{};
};

}  // namespace heapq
