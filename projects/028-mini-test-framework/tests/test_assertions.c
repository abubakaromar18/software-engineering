/* The assertion macros on their passing paths, and their message text on
 * failing paths (captured by running a probe test in a nested context). */
#include <string.h>

#include "internal.h"

TEST(assertions, all_kinds_pass_on_good_values)
{
    const char *name = "mtest";
    double third = 1.0 / 3.0;
    unsigned char a[] = {1, 2, 3}, b[] = {1, 2, 3};

    ASSERT_TRUE(1 + 1 == 2);
    ASSERT_FALSE(0);
    ASSERT_EQ_INT(-3, -3);
    ASSERT_NE_INT(1, 2);
    ASSERT_LT_INT(-5, 5);
    ASSERT_LE_INT(5, 5);
    ASSERT_GT_INT(6, 5);
    ASSERT_GE_INT(6, 6);
    ASSERT_EQ_UINT(sizeof a, 3u);
    ASSERT_NE_UINT(0u, 1u);
    ASSERT_STREQ(name, "mtest");
    ASSERT_STRNE(name, "ntest");
    ASSERT_STREQ(NULL, NULL);           /* two NULLs are equal */
    ASSERT_STRNE(name, NULL);
    ASSERT_NEAR(third * 3.0, 1.0, 1e-12);
    ASSERT_NULL(NULL);
    ASSERT_NOT_NULL(name);
    ASSERT_MEMEQ(a, b, sizeof a);
    ASSERT_MEMEQ(a, "x", 0);            /* zero bytes always match */
}

static int g_calls;
static int next_value(void) { return ++g_calls; }

TEST(assertions, evaluate_arguments_exactly_once)
{
    g_calls = 0;
    ASSERT_EQ_INT(next_value(), 1);
    ASSERT_EQ_INT(g_calls, 1);
    EXPECT_STREQ((g_calls++, "x"), "x");
    EXPECT_EQ_INT(g_calls, 2);
}

/* ---- Failure messages ------------------------------------------------- */

static void (*g_probe)(void);
static void probe_thunk(void *unused) { (void)unused; g_probe(); }

/* Runs fn as an in-process test, nested inside the current one, and
 * stores its result in r (caller frees it with mt_result_free). */
static void run_probe(void (*fn)(void), mt_result *r)
{
    static mt_test probe = {"probe", "probe", __FILE__, __LINE__, probe_thunk, NULL, NULL};
    mt_options opts;
    mt_options_defaults(&opts);
    opts.use_fork = 0;
    g_probe = fn;
    mt_run_one(&probe, &opts, r);
}

static void fail_int(void) { int x = 4; ASSERT_EQ_INT(x, 5); }
static void fail_str(void) { ASSERT_STREQ("abc", NULL); }
static void fail_mem(void) { ASSERT_MEMEQ("abcd", "abXd", 4); }
static void fail_near(void) { ASSERT_NEAR(1.0, 1.5, 0.1); }
static void fail_custom(void) { FAIL("custom %s #%d", "reason", 7); }

static int message_contains(const mt_result *r, const char *needle)
{
    return r->failures && strstr(r->failures->message, needle) != NULL;
}

TEST(assertions, int_failure_shows_expression_and_values)
{
    mt_result r;
    run_probe(fail_int, &r);
    EXPECT_EQ_INT(r.status, MT_FAIL);
    EXPECT_TRUE(message_contains(&r, "expected x == 5"));
    EXPECT_TRUE(message_contains(&r, "left:  4"));
    EXPECT_TRUE(message_contains(&r, "right: 5"));
    mt_result_free(&r);
}

TEST(assertions, string_failure_quotes_values_and_shows_null)
{
    mt_result r;
    run_probe(fail_str, &r);
    EXPECT_TRUE(message_contains(&r, "left:  \"abc\""));
    EXPECT_TRUE(message_contains(&r, "right: NULL"));
    mt_result_free(&r);
}

TEST(assertions, memory_failure_reports_first_differing_offset)
{
    mt_result r;
    run_probe(fail_mem, &r);
    EXPECT_TRUE(message_contains(&r, "offset 2: 0x63 vs 0x58"));
    mt_result_free(&r);
}

TEST(assertions, near_failure_reports_diff)
{
    mt_result r;
    run_probe(fail_near, &r);
    EXPECT_TRUE(message_contains(&r, "within 0.1 of 1.5"));
    EXPECT_TRUE(message_contains(&r, "diff:  0.5"));
    mt_result_free(&r);
}

TEST(assertions, fail_macro_formats_message)
{
    mt_result r;
    run_probe(fail_custom, &r);
    ASSERT_NOT_NULL(r.failures);
    EXPECT_STREQ(r.failures->message, "custom reason #7");
    EXPECT_STREQ(r.failures->file, __FILE__);   /* points at the FAIL() site */
    mt_result_free(&r);
}
