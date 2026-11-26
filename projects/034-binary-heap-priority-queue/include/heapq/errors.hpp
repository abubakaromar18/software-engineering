// errors.hpp — exception types raised when a heap's preconditions are violated.
//
// Contract violations that a caller can reasonably trigger at runtime (popping
// an empty queue, pushing a duplicate key) throw instead of being undefined
// behaviour. Each type derives from the closest standard exception, so callers
// can catch either the specific or the general type.
#pragma once

#include <stdexcept>

namespace heapq {

/// Thrown by top()/pop() on an empty heap.
class EmptyHeapError : public std::out_of_range {
public:
    EmptyHeapError() : std::out_of_range("heap is empty") {}
};

/// Thrown by IndexedHeap::push when the key is already present.
class DuplicateKeyError : public std::invalid_argument {
public:
    DuplicateKeyError() : std::invalid_argument("key is already in the heap") {}
};

/// Thrown when an IndexedHeap operation names a key that is not present.
class MissingKeyError : public std::out_of_range {
public:
    MissingKeyError() : std::out_of_range("key is not in the heap") {}
};

/// Thrown by IndexedHeap::decrease_key when the new priority would make the
/// entry leave the heap *later* than it does now.
class PriorityDirectionError : public std::invalid_argument {
public:
    PriorityDirectionError()
        : std::invalid_argument("decrease_key would move the entry away from the top; use update()") {}
};

}  // namespace heapq
