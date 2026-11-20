/*
 * Runner behaviour: outcomes, fixture life cycle, and fork-mode isolation.
 * Each case builds an unregistered mt_test by hand and runs it nested
 * inside the current test via mt_run_one().
 */
#define _POSIX_C_SOURCE 200809L
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "internal.h"

/* ---- Probe bodies (never registered, so the runner never sees them) -- */

static int g_reached_end;
static char g_log[64];   /* life-cycle trace, e.g. "SBT" */

static void log_step(char c)
{
    size_t n = strlen(g_log);
    if (n + 1 < sizeof g_log) {
        g_log[n] = c;
        g_log[n + 1] = '\0';
    }
}

static void body_pass(void *fx) { (void)fx; EXPECT_TRUE(1); g_reached_end = 1; }
static void body_two_expects(void *fx)
{
    (void)fx;
    EXPECT_EQ_INT(1, 2);
    EXPECT_STREQ("a", "b");
    g_reached_end = 1;   /* EXPECT_* must not stop the test */
}
static void body_assert_stops(void *fx)
{
    (void)fx;
    ASSERT_TRUE(0);
    g_reached_end = 1;
}
static void body_skip(void *fx) { (void)fx; SKIP("needs a GPU"); }
static void body_fail_then_skip(void *fx) { (void)fx; ADD_FAILURE("boom"); SKIP("later"); }
static void body_segfault(void *fx) { (void)fx; ADD_FAILURE("before crash"); raise(SIGSEGV); }
static void body_hang(void *fx) { (void)fx; for (;;) pause(); }
static void body_exit_early(void *fx) { (void)fx; exit(0); }
static void body_touch_global(void *fx) { (void)fx; g_reached_end = 42; }

/* A fixture whose behaviour each test can steer. */
typedef struct { int value; } probe_fx;
static int g_setup_fails;

static void fx_setup(void *p)
{
    log_step('S');
    ((probe_fx *)p)->value = 7;
    if (g_setup_fails)
        ASSERT_TRUE(0);
}
static void fx_teardown(void *p) { (void)p; log_step('T'); }
static void fx_body_ok(void *p) { log_step('B'); EXPECT_EQ_INT(((probe_fx *)p)->value, 7); }
static void fx_body_fatal(void *p) { (void)p; log_step('B'); ASSERT_TRUE(0); log_step('X'); }

static const mt_fixture_def probe_fixture = {sizeof(probe_fx), fx_setup, fx_teardown};

/* ---- Helpers ---------------------------------------------------------- */

static void run(void (*fn)(void *), const mt_fixture_def *fx, int use_fork,
                unsigned timeout, mt_result *r)
{
    mt_test t = {"probe", "case", __FILE__, __LINE__, fn, fx, NULL};
    mt_options opts;
    mt_options_defaults(&opts);
    opts.use_fork = use_fork;
    opts.timeout_secs = timeout;
    g_reached_end = 0;
    g_log[0] = '\0';
    g_setup_fails = 0;
    mt_run_one(&t, &opts, r);
}

static size_t count_failures(const mt_result *r)
{
    size_t n = 0;
    for (const mt_failure *f = r->failures; f; f = f->next)
        n++;
    return n;
}

/* ---- Outcomes (both execution modes) ---------------------------------- */

TEST(runner, passing_test_passes)
{
    mt_result r;
    run(body_pass, NULL, 0, 0, &r);
    EXPECT_EQ_INT(r.status, MT_PASS);
    EXPECT_NULL(r.failures);
    EXPECT_TRUE(g_reached_end);
    mt_result_free(&r);
}

TEST(runner, expect_failures_accumulate_and_continue)
{
    for (int fork_mode = 0; fork_mode <= 1; fork_mode++) {
        mt_result r;
        run(body_two_expects, NULL, fork_mode, 0, &r);
        EXPECT_EQ_INT(r.status, MT_FAIL);
        EXPECT_EQ_UINT(count_failures(&r), 2);
        if (!fork_mode)
            EXPECT_TRUE(g_reached_end);
        mt_result_free(&r);
    }
}

TEST(runner, assert_failure_ends_the_test)
{
    mt_result r;
    run(body_assert_stops, NULL, 0, 0, &r);
    EXPECT_EQ_INT(r.status, MT_FAIL);
    EXPECT_FALSE(g_reached_end);
    mt_result_free(&r);
}

TEST(runner, skip_records_reason_in_both_modes)
{
    for (int fork_mode = 0; fork_mode <= 1; fork_mode++) {
        mt_result r;
        run(body_skip, NULL, fork_mode, 0, &r);
        EXPECT_EQ_INT(r.status, MT_SKIP);
        EXPECT_STREQ(r.detail, "needs a GPU");
        mt_result_free(&r);
    }
}

TEST(runner, skip_never_hides_an_earlier_failure)
{
    mt_result r;
    run(body_fail_then_skip, NULL, 0, 0, &r);
    EXPECT_EQ_INT(r.status, MT_FAIL);
    mt_result_free(&r);
}

/* ---- Fixture life cycle ----------------------------------------------- */

TEST(fixtures, setup_body_teardown_in_order)
{
    mt_result r;
    run(fx_body_ok, &probe_fixture, 0, 0, &r);
    EXPECT_EQ_INT(r.status, MT_PASS);
    EXPECT_STREQ(g_log, "SBT");
    mt_result_free(&r);
}

TEST(fixtures, teardown_runs_after_fatal_body_failure)
{
    mt_result r;
    run(fx_body_fatal, &probe_fixture, 0, 0, &r);
    EXPECT_EQ_INT(r.status, MT_FAIL);
    EXPECT_STREQ(g_log, "SBT");   /* no 'X': the body stopped at the ASSERT */
    mt_result_free(&r);
}

TEST(fixtures, failed_setup_skips_body_and_teardown)
{
    mt_result r;
    mt_test t = {"probe", "case", __FILE__, __LINE__, fx_body_ok, &probe_fixture, NULL};
    mt_options opts;
    mt_options_defaults(&opts);
    opts.use_fork = 0;
    g_log[0] = '\0';
    g_setup_fails = 1;
    mt_run_one(&t, &opts, &r);
    g_setup_fails = 0;

    EXPECT_EQ_INT(r.status, MT_FAIL);
    EXPECT_STREQ(g_log, "S");
    mt_result_free(&r);
}

/* ---- Fork-mode isolation ---------------------------------------------- */

TEST(fork, crash_is_contained_and_reported)
{
    mt_result r;
    run(body_segfault, NULL, 1, 0, &r);
    EXPECT_EQ_INT(r.status, MT_CRASH);
    ASSERT_NOT_NULL(r.detail);
    EXPECT_NOT_NULL(strstr(r.detail, "signal"));
    /* The failure streamed before the crash is not lost. */
    ASSERT_NOT_NULL(r.failures);
    EXPECT_STREQ(r.failures->message, "before crash");
    mt_result_free(&r);
}

TEST(fork, timeout_kills_hanging_test)
{
    mt_result r;
    run(body_hang, NULL, 1, 1, &r);
    EXPECT_EQ_INT(r.status, MT_TIMEOUT);
    EXPECT_STREQ(r.detail, "exceeded 1s timeout");
    EXPECT_GE_INT((long long)(r.seconds * 1000), 900);
    mt_result_free(&r);
}

TEST(fork, exit_inside_a_test_is_not_a_pass)
{
    mt_result r;
    run(body_exit_early, NULL, 1, 0, &r);
    EXPECT_EQ_INT(r.status, MT_CRASH);
    EXPECT_STREQ(r.detail, "test exited early with status 0");
    mt_result_free(&r);
}

TEST(fork, child_state_does_not_leak_into_parent)
{
    mt_result r;
    run(body_touch_global, NULL, 1, 0, &r);
    EXPECT_EQ_INT(r.status, MT_PASS);
    EXPECT_EQ_INT(g_reached_end, 0);
    mt_result_free(&r);
}

/* ---- Ordering --------------------------------------------------------- */

TEST(shuffle, same_seed_same_order_and_a_permutation)
{
    mt_test items[8];
    mt_test *a[8], *b[8];
    for (int i = 0; i < 8; i++) {
        memset(&items[i], 0, sizeof items[i]);
        a[i] = b[i] = &items[i];
    }
    mt_shuffle(a, 8, 12345);
    mt_shuffle(b, 8, 12345);
    EXPECT_MEMEQ(a, b, sizeof a);

    int seen[8] = {0}, moved = 0;
    for (int i = 0; i < 8; i++) {
        seen[a[i] - items]++;
        moved += a[i] != &items[i];
    }
    for (int i = 0; i < 8; i++)
        EXPECT_EQ_INT(seen[i], 1);
    EXPECT_GT_INT(moved, 0);
}
