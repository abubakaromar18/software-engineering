/*
 * A suite with one test per possible outcome. It is *meant* to fail: the
 * end-to-end script (tests/selftest.sh) runs it with different flags and
 * checks the exit codes, console output and JUnit XML it produces.
 */
#define _POSIX_C_SOURCE 200809L
#include <signal.h>
#include <unistd.h>

#include "mtest.h"

TEST(math, addition_works)
{
    EXPECT_EQ_INT(2 + 2, 4);
}

TEST(math, broken_multiplication)
{
    EXPECT_EQ_INT(6 * 7, 41);
    EXPECT_STREQ("<answer>", "&answer");   /* exercises XML escaping */
}

TEST(math, skipped_on_purpose)
{
    SKIP("not implemented yet");
}

TEST(platform, segfaults)
{
    raise(SIGSEGV);
}

TEST(platform, hangs)
{
    for (;;)
        pause();
}

FIXTURE(counter) {
    int n;
};
FIXTURE_SETUP(counter) { self->n = 1; }
FIXTURE_TEARDOWN(counter) {}

TEST_F(counter, starts_at_one)
{
    EXPECT_EQ_INT(self->n, 1);
}
