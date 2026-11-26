#include "heapq/heap_sort.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <deque>
#include <functional>
#include <random>
#include <string>
#include <vector>

namespace {

TEST(HeapSort, TrivialInputs) {
    std::vector<int> empty;
    heapq::heap_sort(empty);
    EXPECT_TRUE(empty.empty());

    std::vector<int> one{7};
    heapq::heap_sort(one);
    EXPECT_EQ(one, std::vector<int>{7});
}

TEST(HeapSort, SortedReversedAndDuplicates) {
    std::vector<int> sorted{1, 2, 3, 4, 5};
    std::vector<int> reversed{5, 4, 3, 2, 1};
    std::vector<int> dups{3, 1, 3, 1, 2, 2};
    heapq::heap_sort(sorted);
    heapq::heap_sort(reversed);
    heapq::heap_sort(dups);
    EXPECT_EQ(sorted, (std::vector<int>{1, 2, 3, 4, 5}));
    EXPECT_EQ(reversed, (std::vector<int>{1, 2, 3, 4, 5}));
    EXPECT_EQ(dups, (std::vector<int>{1, 1, 2, 2, 3, 3}));
}

TEST(HeapSort, CustomComparatorSortsDescending) {
    std::vector<std::string> words{"pear", "apple", "fig", "banana"};
    heapq::heap_sort(words, std::ranges::greater{});
    EXPECT_EQ(words, (std::vector<std::string>{"pear", "fig", "banana", "apple"}));
}

TEST(HeapSort, WorksOnSubrangesAndOtherContainers) {
    std::vector<int> v{9, 5, 3, 7, 1, 0};
    heapq::heap_sort(v.begin() + 1, v.end() - 1);  // sorts {5, 3, 7, 1}
    EXPECT_EQ(v, (std::vector<int>{9, 1, 3, 5, 7, 0}));

    std::deque<int> d{4, 2, 3, 1};
    heapq::heap_sort(d);
    EXPECT_EQ(d, (std::deque<int>{1, 2, 3, 4}));
}

TEST(HeapSort, UsableInConstantExpressions) {
    constexpr auto sorted = [] {
        std::array<int, 5> a{4, 1, 5, 2, 3};
        heapq::heap_sort(a);
        return a;
    }();
    static_assert(sorted == std::array<int, 5>{1, 2, 3, 4, 5});
    SUCCEED();
}

TEST(HeapSort, AgreesWithStdSortOnRandomInputs) {
    std::mt19937 rng(7);
    for (std::size_t n : {2u, 3u, 10u, 1'000u, 50'000u}) {
        std::vector<int> data(n);
        std::uniform_int_distribution<int> dist(-500, 500);
        std::ranges::generate(data, [&] { return dist(rng); });
        auto expected = data;
        std::ranges::sort(expected);
        heapq::heap_sort(data);
        ASSERT_EQ(data, expected) << "n = " << n;
    }
}

}  // namespace
