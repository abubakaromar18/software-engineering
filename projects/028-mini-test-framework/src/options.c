/* Command-line parsing for test binaries. Pure: no globals, no exit(). */
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "internal.h"

void mt_options_defaults(mt_options *opts)
{
    memset(opts, 0, sizeof *opts);
    opts->use_fork = 1;
    opts->color = -1;
}

/* If arg is "--name=value" returns value, otherwise NULL. */
static const char *value_of(const char *arg, const char *name)
{
    size_t n = strlen(name);
    if (strncmp(arg, name, n) == 0 && arg[n] == '=')
        return arg + n + 1;
    return NULL;
}

static int parse_u64(const char *s, unsigned long long max, unsigned long long *out)
{
    if (!*s || *s == '-')
        return -1;
    char *end;
    errno = 0;
    unsigned long long v = strtoull(s, &end, 10);
    if (errno || *end || v > max)
        return -1;
    *out = v;
    return 0;
}

int mt_options_parse(mt_options *opts, int argc, char **argv,
                     char *err, size_t err_size)
{
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        const char *v;
        unsigned long long n;

        if (strcmp(a, "-h") == 0 || strcmp(a, "--help") == 0) {
            opts->show_help = 1;
        } else if (strcmp(a, "--list") == 0) {
            opts->list_only = 1;
        } else if (strcmp(a, "--no-fork") == 0) {
            opts->use_fork = 0;
        } else if (strcmp(a, "--fail-fast") == 0) {
            opts->fail_fast = 1;
        } else if (strcmp(a, "--shuffle") == 0) {
            opts->shuffle = 1;
        } else if (strcmp(a, "-v") == 0 || strcmp(a, "--verbose") == 0) {
            opts->verbose = 1;
        } else if (strcmp(a, "--color") == 0) {
            opts->color = 1;
        } else if (strcmp(a, "--no-color") == 0) {
            opts->color = 0;
        } else if ((v = value_of(a, "--filter"))) {
            opts->filter = v;
        } else if ((v = value_of(a, "--junit"))) {
            if (!*v) {
                snprintf(err, err_size, "--junit needs a file path");
                return -1;
            }
            opts->junit_path = v;
        } else if ((v = value_of(a, "--timeout"))) {
            if (parse_u64(v, UINT_MAX, &n) != 0) {
                snprintf(err, err_size, "invalid --timeout value '%s'", v);
                return -1;
            }
            opts->timeout_secs = (unsigned)n;
        } else if ((v = value_of(a, "--seed"))) {
            if (parse_u64(v, UINT64_MAX, &n) != 0 || n == 0) {
                snprintf(err, err_size, "invalid --seed value '%s' (must be > 0)", v);
                return -1;
            }
            opts->seed = n;
            opts->shuffle = 1;   /* a seed only makes sense when shuffling */
        } else {
            snprintf(err, err_size, "unknown option '%s'", a);
            return -1;
        }
    }
    return 0;
}

void mt_options_usage(FILE *out, const char *prog)
{
    fprintf(out,
        "usage: %s [options]\n"
        "\n"
        "  --filter=PATTERNS  comma-separated globs over suite.name;\n"
        "                     prefix with '-' to exclude (e.g. 'math.*,-math.slow*')\n"
        "  --list             list selected tests and exit\n"
        "  --junit=FILE       also write a JUnit XML report to FILE\n"
        "  --timeout=SECS     kill a test after SECS seconds (fork mode)\n"
        "  --no-fork          run tests in-process (easier under a debugger,\n"
        "                     but a crash takes the whole run down)\n"
        "  --fail-fast        stop after the first failing test\n"
        "  --shuffle          run tests in random order\n"
        "  --seed=N           shuffle with a fixed seed (implies --shuffle)\n"
        "  --color/--no-color force colored output on or off\n"
        "  -v, --verbose      show every test, not just failures\n"
        "  -h, --help         show this help\n"
        "\n"
        "Exit status: 0 all passed, 1 failures, 2 usage error.\n",
        prog);
}
