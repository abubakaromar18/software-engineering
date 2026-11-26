#include "heapq/indexed_heap.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <limits>
#include <map>
#include <random>
#include <string>
#include <vector>

namespace {

using Heap = heapq::IndexedHeap<std::string, int>;

TEST(IndexedHeap, PushPopOrder) {
    Heap heap;
    heap.push("c", 30);
    heap.push("a", 10);
    heap.push("b", 20);
    EXPECT_EQ(heap.top().key, "a");
    EXPECT_EQ(heap.pop().key, "a");
    EXPECT_EQ(heap.pop().key, "b");
    EXPECT_EQ(heap.pop().key, "c");
    EXPECT_TRUE(heap.empty());
}

TEST(IndexedHeap, DuplicateKeyThrowsAndLeavesHeapUnchanged) {
    Heap heap;
    heap.push("x", 1);
    EXPECT_THROW(heap.push("x", 0), heapq::DuplicateKeyError);
    EXPECT_EQ(heap.size(), 1u);
    EXPECT_EQ(heap.priority_of("x"), 1);
    EXPECT_TRUE(heap.check_invariants());
}

TEST(IndexedHeap, MissingKeyOperationsThrow) {
    Heap heap;
    EXPECT_THROW((void)heap.priority_of("nope"), heapq::MissingKeyError);
    EXPECT_THROW(heap.decrease_key("nope", 1), heapq::MissingKeyError);
    EXPECT_THROW(heap.update("nope", 1), heapq::MissingKeyError);
    EXPECT_FALSE(heap.erase("nope").has_value());
    EXPECT_THROW(heap.pop(), heapq::EmptyHeapError);
}

TEST(IndexedHeap, DecreaseKeyMovesEntryToTop) {
    Heap heap;
    for (int i = 0; i < 10; ++i) heap.push("k" + std::to_string(i), 100 + i);
    heap.decrease_key("k9", 1);
    EXPECT_TRUE(heap.check_invariants());
    EXPECT_EQ(heap.top().key, "k9");
    EXPECT_EQ(heap.priority_of("k9"), 1);
}

TEST(IndexedHeap, DecreaseKeyRejectsWrongDirection) {
    Heap heap;
    heap.push("a", 5);
    EXPECT_THROW(heap.decrease_key("a", 6), heapq::PriorityDirectionError);
    EXPECT_EQ(heap.priority_of("a"), 5);
    EXPECT_NO_THROW(heap.decrease_key("a", 5));  // equal priority is allowed
}

TEST(IndexedHeap, UpdateMovesInEitherDirection) {
    Heap heap;
    heap.push("a", 1);
    heap.push("b", 2);
    heap.push("c", 3);
    heap.update("a", 10);  // sinks
    EXPECT_EQ(heap.top().key, "b");
    heap.update("c", 0);   // rises
    EXPECT_EQ(heap.top().key, "c");
    EXPECT_TRUE(heap.check_invariants());
}

TEST(IndexedHeap, EraseFromMiddle) {
    Heap heap;
    for (int i = 0; i < 20; ++i) heap.push(std::to_string(i), i);
    auto removed = heap.erase("7");
    ASSERT_TRUE(removed.has_value());
    EXPECT_EQ(removed->priority, 7);
    EXPECT_FALSE(heap.contains("7"));
    EXPECT_TRUE(heap.check_invariants());
    EXPECT_EQ(heap.size(), 19u);
}

TEST(IndexedHeap, MaxHeapComparator) {
    heapq::IndexedHeap<int, double, std::greater<double>> heap;
    heap.push(1, 0.5);
    heap.push(2, 2.5);
    heap.push(3, 1.5);
    EXPECT_EQ(heap.pop().key, 2);
    heap.decrease_key(1, 9.0);  // "decrease" means "move towards the top"
    EXPECT_EQ(heap.top().key, 1);
}

TEST(IndexedHeap, IterationVisitsEveryEntry) {
    Heap heap;
    heap.push("a", 3);
    heap.push("b", 1);
    heap.push("c", 2);
    std::vector<std::string> keys;
    for (const auto& entry : heap) keys.push_back(entry.key);
    std::ranges::sort(keys);
    EXPECT_EQ(keys, (std::vector<std::string>{"a", "b", "c"}));
}

// Property test against a std::map model of key -> priority.
TEST(IndexedHeap, MatchesModelUnderRandomOperations) {
    std::mt19937 rng(34);
    std::uniform_int_distribution<int> key_dist(0, 199);
    std::uniform_int_distribution<int> prio_dist(0, 10'000);
    std::uniform_int_distribution<int> op_dist(0, 4);

    heapq::IndexedHeap<int, int> heap;
    std::map<int, int> model;

    auto model_min = [&] {
        return std::ranges::min_element(model, {}, [](const auto& kv) { return kv.second; })->second;
    };

    for (int step = 0; step < 20'000; ++step) {
        const int key = key_dist(rng);
        const int prio = prio_dist(rng);
        switch (op_dist(rng)) {
            case 0:
            case 1:
                if (!model.contains(key)) {
                    heap.push(key, prio);
                    model[key] = prio;
                }
                break;
            case 2:
                if (model.contains(key)) {
                    const int lower = std::min(prio, model[key]);
                    heap.decrease_key(key, lower);
                    model[key] = lower;
                }
                break;
            case 3:
                ASSERT_EQ(heap.erase(key).has_value(), model.erase(key) == 1);
                break;
            case 4:
                if (!model.empty()) {
                    const int expected = model_min();
                    const auto entry = heap.pop();
                    ASSERT_EQ(entry.priority, expected);
                    ASSERT_EQ(model.at(entry.key), expected);
                    model.erase(entry.key);
                }
                break;
        }
        ASSERT_EQ(heap.size(), model.size());
        if (step % 500 == 0) {
            ASSERT_TRUE(heap.check_invariants());
        }
    }
    ASSERT_TRUE(heap.check_invariants());
}

}  // namespace
