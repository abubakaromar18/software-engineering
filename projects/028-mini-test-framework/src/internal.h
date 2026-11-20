/*
 * Internal interfaces shared by the framework's modules. Not installed and
 * not part of the public API; the self-tests include it to unit-test the
 * pure pieces (filtering, option parsing, XML escaping).
 */
#ifndef MTEST_INTERNAL_H
#define MTEST_INTERNAL_H

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>

#include "mtest.h"

/* ---- Results --------------------------------------------------------- */

typedef enum {
    MT_PASS,
    MT_FAIL,     /* one or more assertions failed */
    MT_SKIP,     /* SKIP() was called */
    MT_CRASH,    /* killed by a signal or exited unexpectedly (fork mode) */
    MT_TIMEOUT   /* exceeded --timeout (fork mode) */
} mt_status;

typedef struct mt_failure {
    char *file;
    int line;
    char *message;
    struct mt_failure *next;
} mt_failure;

typedef struct mt_result {
    const mt_test *test;
    mt_status status;
    mt_failure *failures;      /* in the order they were recorded */
    char *detail;              /* skip reason or crash description; may be NULL */
    double seconds;
} mt_result;

typedef struct mt_summary {
    size_t total, passed, failed, skipped, errored; /* errored = crash+timeout */
    double seconds;
    uint64_t seed;             /* 0 when not shuffled */
} mt_summary;

const char *mt_status_name(mt_status status);
int mt_status_is_bad(mt_status status);
void mt_result_add_failure(mt_result *r, const char *file, int line, const char *msg);
void mt_result_free(mt_result *r);

/* ---- Options (options.c) --------------------------------------------- */

typedef struct mt_options {
    const char *filter;        /* comma-separated globs, '-' prefix excludes */
    const char *junit_path;    /* NULL = no JUnit report */
    int list_only;
    int use_fork;              /* run each test in a child process */
    unsigned timeout_secs;     /* 0 = none; fork mode only */
    int fail_fast;
    int shuffle;
    uint64_t seed;             /* used when shuffle is set; 0 = pick one */
    int color;                 /* -1 auto, 0 off, 1 on */
    int verbose;               /* print RUN lines and passing tests */
    int show_help;
} mt_options;

void mt_options_defaults(mt_options *opts);

/* Returns 0 on success; on error writes a message into err and returns -1. */
int mt_options_parse(mt_options *opts, int argc, char **argv,
                     char *err, size_t err_size);
void mt_options_usage(FILE *out, const char *prog);

/* ---- Filtering (filter.c) -------------------------------------------- */

/* Shell-style glob: '*' matches any run, '?' any one character. */
int mt_glob_match(const char *pattern, const char *text);

/* Applies a filter expression to "suite.name". A NULL or empty filter
 * selects everything. Positive patterns are OR-ed; any matching negative
 * pattern ("-suite.*") excludes. Only negatives => start from "all". */
int mt_filter_match(const char *filter, const char *full_name);

/* ---- Registry (registry.c) ------------------------------------------- */

/* Returns a freshly allocated array of the registered tests that pass the
 * filter, sorted by (file, line) for a stable declaration order. */
mt_test **mt_registry_select(const char *filter, size_t *count);

/* Deterministic Fisher-Yates shuffle driven by splitmix64(seed). */
void mt_shuffle(mt_test **tests, size_t count, uint64_t seed);

/* ---- Assertion context (assert.c) ------------------------------------ */

#include <setjmp.h>

typedef struct mt_context {
    mt_result *result;
    jmp_buf jump;              /* where fatal assertions / SKIP land */
    int report_fd;             /* >= 0 in a forked child: stream records */
    struct mt_context *prev;   /* enclosing context (nested runs) */
} mt_context;

/* Pushes/pops the context that assertions report into. */
void mt_context_enter(mt_context *ctx);
void mt_context_leave(void);

/* Record wire format between a forked child and the runner. */
enum { MT_REC_FAILURE = 'F', MT_REC_SKIP = 'S', MT_REC_DONE = 'D' };
int mt_record_write(int fd, char kind, const char *file, int line, const char *msg);
/* Reads every record from fd until EOF and applies them to r. Sets *done
 * when the child reported that the test ran to completion. */
int mt_record_read_all(int fd, mt_result *r, int *done);

/* ---- Runner (runner.c) ----------------------------------------------- */

void mt_run_one(const mt_test *test, const mt_options *opts, mt_result *out);

/* ---- Reporters ------------------------------------------------------- */

typedef struct mt_reporter {
    void *state;
    void (*begin)(void *state, size_t total, const mt_summary *s);
    void (*test_start)(void *state, const mt_test *test);
    void (*test_done)(void *state, const mt_result *result);
    /* results stay valid until end() returns */
    int (*end)(void *state, const mt_result *results, size_t n, const mt_summary *s);
    void (*destroy)(void *state);
} mt_reporter;

int mt_console_reporter(mt_reporter *rep, FILE *out, int color, int verbose);
int mt_junit_reporter(mt_reporter *rep, const char *path);

/* Writes s XML-escaped (for both text and attribute content) to out. */
void mt_xml_escape(FILE *out, const char *s);

/* ---- Small utilities (util.c) ---------------------------------------- */

char *mt_strdup(const char *s);
char *mt_vformat(const char *fmt, va_list ap);
double mt_now_seconds(void);

#endif /* MTEST_INTERNAL_H */
