#include <gtest/gtest.h>

#include <limits>

#include "vfs/text.hpp"

using vfs::glob_match;
using vfs::human_size;

TEST(Glob, Literals) {
    EXPECT_TRUE(glob_match("abc", "abc"));
    EXPECT_FALSE(glob_match("abc", "abd"));
    EXPECT_FALSE(glob_match("abc", "ab"));
    EXPECT_TRUE(glob_match("", ""));
    EXPECT_FALSE(glob_match("", "a"));
}

TEST(Glob, Star) {
    EXPECT_TRUE(glob_match("*", ""));
    EXPECT_TRUE(glob_match("*", "anything"));
    EXPECT_TRUE(glob_match("*.cpp", "main.cpp"));
    EXPECT_FALSE(glob_match("*.cpp", "main.hpp"));
    EXPECT_TRUE(glob_match("a*b*c", "aXXbYYc"));
    EXPECT_TRUE(glob_match("**a", "a"));
}

TEST(Glob, StarNeedsBacktracking) {
    // The first 'b' is a false lead; the matcher must retry from the star.
    EXPECT_TRUE(glob_match("a*bc", "abbbc"));
    EXPECT_TRUE(glob_match("*ab", "aab"));
    EXPECT_FALSE(glob_match("a*bc", "abcb"));
}

TEST(Glob, QuestionMark) {
    EXPECT_TRUE(glob_match("?.md", "a.md"));
    EXPECT_FALSE(glob_match("?.md", ".md"));
    EXPECT_TRUE(glob_match("t?st_*.cpp", "test_node.cpp"));
}

TEST(Glob, IsCaseSensitive) { EXPECT_FALSE(glob_match("readme*", "README.md")); }

TEST(HumanSize, Bytes) {
    EXPECT_EQ(human_size(0), "0 B");
    EXPECT_EQ(human_size(1023), "1023 B");
}

TEST(HumanSize, BinaryUnits) {
    EXPECT_EQ(human_size(1024), "1.0 KiB");
    EXPECT_EQ(human_size(1536), "1.5 KiB");
    EXPECT_EQ(human_size(5ull * 1024 * 1024), "5.0 MiB");
    EXPECT_EQ(human_size(3ull << 30), "3.0 GiB");
}

TEST(HumanSize, LargestValueDoesNotOverflowUnitTable) {
    EXPECT_EQ(human_size(std::numeric_limits<std::uint64_t>::max()), "16.0 EiB");
}
