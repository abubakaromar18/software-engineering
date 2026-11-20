/* Unit tests for command-line parsing. */
#include "internal.h"

/* Parses a NULL-terminated argument list (argv[0] is supplied). */
static int parse(mt_options *o, char *err, size_t n, char **args)
{
    char *argv[16] = {"prog"};
    int argc = 1;
    while (args[argc - 1] && argc < 16) {
        argv[argc] = args[argc - 1];
        argc++;
    }
    mt_options_defaults(o);
    return mt_options_parse(o, argc, argv, err, n);
}

TEST(options, defaults_fork_and_auto_color)
{
    mt_options o;
    char err[128];
    char *none[] = {NULL};
    ASSERT_EQ_INT(parse(&o, err, sizeof err, none), 0);
    EXPECT_TRUE(o.use_fork);
    EXPECT_EQ_INT(o.color, -1);
    EXPECT_NULL(o.filter);
    EXPECT_EQ_UINT(o.timeout_secs, 0);
    EXPECT_FALSE(o.shuffle);
}

TEST(options, parses_every_flag)
{
    mt_options o;
    char err[128];
    char *args[] = {"--filter=a.*", "--junit=out.xml", "--timeout=5", "--no-fork",
                    "--fail-fast", "--no-color", "-v", "--list", NULL};
    ASSERT_EQ_INT(parse(&o, err, sizeof err, args), 0);
    EXPECT_STREQ(o.filter, "a.*");
    EXPECT_STREQ(o.junit_path, "out.xml");
    EXPECT_EQ_UINT(o.timeout_secs, 5);
    EXPECT_FALSE(o.use_fork);
    EXPECT_TRUE(o.fail_fast);
    EXPECT_EQ_INT(o.color, 0);
    EXPECT_TRUE(o.verbose);
    EXPECT_TRUE(o.list_only);
}

TEST(options, seed_implies_shuffle)
{
    mt_options o;
    char err[128];
    char *args[] = {"--seed=18446744073709551615", NULL};
    ASSERT_EQ_INT(parse(&o, err, sizeof err, args), 0);
    EXPECT_TRUE(o.shuffle);
    EXPECT_EQ_UINT(o.seed, 18446744073709551615ULL);
}

TEST(options, rejects_bad_numbers)
{
    mt_options o;
    char err[128];
    char *bad_timeout[] = {"--timeout=-1", NULL};
    char *junk_timeout[] = {"--timeout=5s", NULL};
    char *zero_seed[] = {"--seed=0", NULL};
    char *empty_seed[] = {"--seed=", NULL};

    EXPECT_EQ_INT(parse(&o, err, sizeof err, bad_timeout), -1);
    EXPECT_EQ_INT(parse(&o, err, sizeof err, junk_timeout), -1);
    EXPECT_STREQ(err, "invalid --timeout value '5s'");
    EXPECT_EQ_INT(parse(&o, err, sizeof err, zero_seed), -1);
    EXPECT_EQ_INT(parse(&o, err, sizeof err, empty_seed), -1);
}

TEST(options, rejects_unknown_and_valueless_options)
{
    mt_options o;
    char err[128];
    char *unknown[] = {"--frobnicate", NULL};
    char *prefix_only[] = {"--filterx=a", NULL};
    char *empty_junit[] = {"--junit=", NULL};

    EXPECT_EQ_INT(parse(&o, err, sizeof err, unknown), -1);
    EXPECT_STREQ(err, "unknown option '--frobnicate'");
    EXPECT_EQ_INT(parse(&o, err, sizeof err, prefix_only), -1);
    EXPECT_EQ_INT(parse(&o, err, sizeof err, empty_junit), -1);
}

TEST(options, help_flag)
{
    mt_options o;
    char err[128];
    char *args[] = {"-h", NULL};
    ASSERT_EQ_INT(parse(&o, err, sizeof err, args), 0);
    EXPECT_TRUE(o.show_help);
}
