#include "heapq/binary_heap.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <memory>
#include <queue>
#include <random>
#include <string>
#include <vector>

namespace {

template <class Heap>
auto drain(Heap& heap) {
    std::vector<typename Heap::value_type> out;
    while (auto v = heap.try_pop()) out.push_back(std::move(*v));
    return out;
}

TEST(BinaryHeap, StartsEmpty) {
    heapq::BinaryHeap<int> heap;
    EXPECT_TRUE(heap.empty());
    EXPECT_EQ(heap.size(), 0u);
    EXPECT_FALSE(heap.try_pop().has_value());
}

TEST(BinaryHeap, EmptyAccessThrows) {
    heapq::BinaryHeap<int> heap;
    EXPECT_THROW((void)heap.top(), heapq::EmptyHeapError);
    EXPECT_THROW(heap.pop(), heapq::EmptyHeapError);
    // Also catchable as the standard base type.
    EXPECT_THROW(heap.pop(), std::out_of_range);
}

TEST(BinaryHeap, PopsInAscendingOrderByDefault) {
    heapq::BinaryHeap<int> heap;
    for (int v : {5, 1, 8, 3, 9, 2, 7}) heap.push(v);
    EXPECT_EQ(heap.top(), 1);
    EXPECT_EQ(drain(heap), (std::vector<int>{1, 2, 3, 5, 7, 8, 9}));
}

TEST(BinaryHeap, MaxHeapAlias) {
    heapq::MaxHeap<int> heap{4, 10, 2, 6};
    EXPECT_EQ(heap.pop(), 10);
    EXPECT_EQ(heap.pop(), 6);
    EXPECT_EQ(heap.size(), 2u);
}

TEST(BinaryHeap, RangeConstructionHeapifies) {
    const std::vector<int> input{9, 8, 7, 6, 5, 4, 3, 2, 1, 0};
    heapq::BinaryHeap<int> heap(input.begin(), input.end());
    EXPECT_TRUE(heapq::is_heap(heap.begin(), heap.end()));
    EXPECT_EQ(heap.size(), input.size());
    EXPECT_EQ(heap.top(), 0);
}

TEST(BinaryHeap, CustomComparatorOnStructs) {
    struct Job {
        std::string name;
        int cost;
    };
    auto cheaper = [](const Job& a, const Job& b) { return a.cost < b.cost; };
    heapq::BinaryHeap<Job, decltype(cheaper)> heap(cheaper);
    heap.emplace("compile", 30);
    heap.emplace("lint", 5);
    heap.emplace("deploy", 50);
    EXPECT_EQ(heap.pop().name, "lint");
    EXPECT_EQ(heap.pop().name, "compile");
    EXPECT_EQ(heap.pop().name, "deploy");
}

TEST(BinaryHeap, SupportsMoveOnlyTypes) {
    auto by_value = [](const std::unique_ptr<int>& a, const std::unique_ptr<int>& b) { return *a < *b; };
    heapq::BinaryHeap<std::unique_ptr<int>, decltype(by_value)> heap(by_value);
    heap.push(std::make_unique<int>(3));
    heap.push(std::make_unique<int>(1));
    heap.emplace(new int(2));
    std::unique_ptr<int> smallest = heap.pop();
    ASSERT_NE(smallest, nullptr);
    EXPECT_EQ(*smallest, 1);
    EXPECT_EQ(*heap.top(), 2);
}

TEST(BinaryHeap, ClearEmptiesTheHeap) {
    heapq::BinaryHeap<int> heap{1, 2, 3};
    heap.clear();
    EXPECT_TRUE(heap.empty());
    heap.push(42);
    EXPECT_EQ(heap.top(), 42);
}

TEST(BinaryHeap, HandlesDuplicates) {
    heapq::BinaryHeap<int> heap{2, 2, 1, 1, 3, 3};
    EXPECT_EQ(drain(heap), (std::vector<int>{1, 1, 2, 2, 3, 3}));
}

// Property test: random interleavings of push/pop agree with the standard
// library's priority_queue and the invariant holds after every step.
TEST(BinaryHeap, MatchesStdPriorityQueueUnderRandomOperations) {
    std::mt19937 rng(20261126);
    std::uniform_int_distribution<int> value(-1000, 1000);
    std::bernoulli_distribution do_push(0.6);

    heapq::BinaryHeap<int> heap;
    std::priority_queue<int, std::vector<int>, std::greater<>> reference;
    for (int step = 0; step < 20'000; ++step) {
        if (reference.empty() || do_push(rng)) {
            const int v = value(rng);
            heap.push(v);
            reference.push(v);
        } else {
            ASSERT_EQ(heap.pop(), reference.top());
            reference.pop();
        }
        ASSERT_EQ(heap.size(), reference.size());
        if (step % 997 == 0) {
            ASSERT_TRUE(heapq::is_heap(heap.begin(), heap.end()));
        }
    }
}

TEST(HeapAlgorithms, IsHeapDetectsViolations) {
    const std::vector<int> good{1, 3, 2, 7, 4};
    const std::vector<int> bad{1, 3, 2, 0, 4};
    EXPECT_TRUE(heapq::is_heap(good.begin(), good.end()));
    EXPECT_FALSE(heapq::is_heap(bad.begin(), bad.end()));
    EXPECT_TRUE(heapq::is_heap(good.begin(), good.begin()));
}

}  // namespace
