/* mt_main(): select -> (shuffle) -> run -> report. */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#include "internal.h"

enum { EXIT_OK = 0, EXIT_TESTS_FAILED = 1, EXIT_USAGE = 2 };

static uint64_t fresh_seed(void)
{
    uint64_t s = (uint64_t)time(NULL) * 6364136223846793005ULL ^ (uint64_t)getpid();
    return s ? s : 1;   /* 0 means "not shuffled" in the summary */
}

static void list_tests(mt_test **tests, size_t n)
{
    for (size_t i = 0; i < n; i++)
        printf("%s.%s  (%s:%d)\n", tests[i]->suite, tests[i]->name,
               tests[i]->file, tests[i]->line);
}

static void tally(mt_summary *sum, const mt_result *r)
{
    sum->total++;
    switch (r->status) {
    case MT_PASS:    sum->passed++; break;
    case MT_FAIL:    sum->failed++; break;
    case MT_SKIP:    sum->skipped++; break;
    case MT_CRASH:
    case MT_TIMEOUT: sum->errored++; break;
    }
}

int mt_main(int argc, char **argv)
{
    const char *prog = argc > 0 ? argv[0] : "tests";
    mt_options opts;
    char err[256];

    mt_options_defaults(&opts);
    if (mt_options_parse(&opts, argc, argv, err, sizeof err) != 0) {
        fprintf(stderr, "%s: %s\n\n", prog, err);
        mt_options_usage(stderr, prog);
        return EXIT_USAGE;
    }
    if (opts.show_help) {
        mt_options_usage(stdout, prog);
        return EXIT_OK;
    }

    size_t n;
    mt_test **tests = mt_registry_select(opts.filter, &n);
    if (!tests) {
        fprintf(stderr, "%s: out of memory\n", prog);
        return EXIT_USAGE;
    }
    if (opts.list_only) {
        list_tests(tests, n);
        free(tests);
        return EXIT_OK;
    }
    /* A filter that silently matches nothing would turn CI green; refuse. */
    if (n == 0 && opts.filter && *opts.filter) {
        fprintf(stderr, "%s: no tests match --filter=%s\n", prog, opts.filter);
        free(tests);
        return EXIT_USAGE;
    }

    mt_summary sum = {0};
    if (opts.shuffle) {
        sum.seed = opts.seed ? opts.seed : fresh_seed();
        mt_shuffle(tests, n, sum.seed);
    }

    mt_reporter reps[2];
    size_t nreps = 0;
    if (mt_console_reporter(&reps[nreps], stdout, opts.color, opts.verbose) == 0)
        nreps++;
    if (opts.junit_path) {
        if (mt_junit_reporter(&reps[nreps], opts.junit_path) != 0) {
            fprintf(stderr, "%s: could not create JUnit reporter\n", prog);
            for (size_t i = 0; i < nreps; i++)
                reps[i].destroy(reps[i].state);
            free(tests);
            return EXIT_USAGE;
        }
        nreps++;
    }

    mt_result *results = calloc(n ? n : 1, sizeof *results);
    if (!results) {
        fprintf(stderr, "%s: out of memory\n", prog);
        for (size_t i = 0; i < nreps; i++)
            reps[i].destroy(reps[i].state);
        free(tests);
        return EXIT_USAGE;
    }

    for (size_t r = 0; r < nreps; r++)
        if (reps[r].begin)
            reps[r].begin(reps[r].state, n, &sum);

    double start = mt_now_seconds();
    size_t ran = 0;
    for (size_t i = 0; i < n; i++) {
        for (size_t r = 0; r < nreps; r++)
            if (reps[r].test_start)
                reps[r].test_start(reps[r].state, tests[i]);

        mt_run_one(tests[i], &opts, &results[i]);
        ran++;
        tally(&sum, &results[i]);

        for (size_t r = 0; r < nreps; r++)
            if (reps[r].test_done)
                reps[r].test_done(reps[r].state, &results[i]);

        if (opts.fail_fast && mt_status_is_bad(results[i].status))
            break;
    }
    sum.seconds = mt_now_seconds() - start;

    int report_error = 0;
    for (size_t r = 0; r < nreps; r++) {
        if (reps[r].end && reps[r].end(reps[r].state, results, ran, &sum) != 0)
            report_error = 1;
        reps[r].destroy(reps[r].state);
    }

    for (size_t i = 0; i < ran; i++)
        mt_result_free(&results[i]);
    free(results);
    free(tests);

    if (sum.failed || sum.errored)
        return EXIT_TESTS_FAILED;
    return report_error ? EXIT_USAGE : EXIT_OK;
}
