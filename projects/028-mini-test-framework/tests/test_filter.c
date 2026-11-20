/* Unit tests for glob matching and filter expressions. */
#include "internal.h"

TEST(glob, literal_match_is_exact)
{
    EXPECT_TRUE(mt_glob_match("math.add", "math.add"));
    EXPECT_FALSE(mt_glob_match("math.add", "math.adds"));
    EXPECT_FALSE(mt_glob_match("math.add", "math.ad"));
}

TEST(glob, star_matches_any_run_including_empty)
{
    EXPECT_TRUE(mt_glob_match("math.*", "math."));
    EXPECT_TRUE(mt_glob_match("math.*", "math.add"));
    EXPECT_TRUE(mt_glob_match("*", ""));
    EXPECT_TRUE(mt_glob_match("*.add", "math.add"));
    EXPECT_FALSE(mt_glob_match("*.add", "math.sub"));
}

TEST(glob, question_mark_matches_exactly_one)
{
    EXPECT_TRUE(mt_glob_match("v?", "v1"));
    EXPECT_FALSE(mt_glob_match("v?", "v"));
    EXPECT_FALSE(mt_glob_match("v?", "v12"));
}

TEST(glob, star_backtracks)
{
    /* The first "b" a greedy matcher sees is the wrong one. */
    EXPECT_TRUE(mt_glob_match("a*b*c", "abxbyc"));
    EXPECT_TRUE(mt_glob_match("*ab", "aab"));
    EXPECT_FALSE(mt_glob_match("a*b*c", "abxbyd"));
    EXPECT_TRUE(mt_glob_match("**x**", "x"));
}

TEST(filter, empty_or_null_selects_everything)
{
    EXPECT_TRUE(mt_filter_match(NULL, "any.test"));
    EXPECT_TRUE(mt_filter_match("", "any.test"));
}

TEST(filter, positives_are_ored)
{
    const char *f = "math.*,io.read";
    EXPECT_TRUE(mt_filter_match(f, "math.add"));
    EXPECT_TRUE(mt_filter_match(f, "io.read"));
    EXPECT_FALSE(mt_filter_match(f, "io.write"));
}

TEST(filter, negatives_exclude_and_win)
{
    const char *f = "math.*,-math.slow_*";
    EXPECT_TRUE(mt_filter_match(f, "math.add"));
    EXPECT_FALSE(mt_filter_match(f, "math.slow_sum"));
}

TEST(filter, only_negatives_start_from_everything)
{
    EXPECT_TRUE(mt_filter_match("-slow.*", "fast.one"));
    EXPECT_FALSE(mt_filter_match("-slow.*", "slow.one"));
}

TEST(filter, ignores_empty_tokens)
{
    EXPECT_TRUE(mt_filter_match(",,math.add,", "math.add"));
    EXPECT_TRUE(mt_filter_match("-", "math.add"));   /* bare '-' excludes nothing */
}
