/* Human-readable progress and summary report, gtest-flavoured. */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "internal.h"

typedef struct {
    FILE *out;
    int color;
    int verbose;
} console_state;

#define C_RED    "\033[31m"
#define C_GREEN  "\033[32m"
#define C_YELLOW "\033[33m"
#define C_RESET  "\033[0m"

static void tag(console_state *s, const char *color, const char *text)
{
    if (s->color)
        fprintf(s->out, "%s%s%s", color, text, C_RESET);
    else
        fputs(text, s->out);
}

static double ms(double seconds) { return seconds * 1000.0; }

static void con_begin(void *state, size_t total, const mt_summary *sum)
{
    console_state *s = state;
    tag(s, C_GREEN, "[==========]");
    fprintf(s->out, " Running %zu test%s", total, total == 1 ? "" : "s");
    if (sum->seed)
        fprintf(s->out, " (shuffled, --seed=%llu)", (unsigned long long)sum->seed);
    fputc('\n', s->out);
}

static void con_test_start(void *state, const mt_test *t)
{
    console_state *s = state;
    if (!s->verbose)
        return;
    tag(s, C_GREEN, "[ RUN      ]");
    fprintf(s->out, " %s.%s\n", t->suite, t->name);
    fflush(s->out);   /* visible before a slow or hanging test starts */
}

static void con_test_done(void *state, const mt_result *r)
{
    console_state *s = state;
    const mt_test *t = r->test;

    switch (r->status) {
    case MT_PASS:
        if (!s->verbose)
            return;
        tag(s, C_GREEN, "[       OK ]");
        break;
    case MT_SKIP:     tag(s, C_YELLOW, "[  SKIPPED ]"); break;
    case MT_FAIL:     tag(s, C_RED,    "[  FAILED  ]"); break;
    case MT_CRASH:    tag(s, C_RED,    "[  CRASHED ]"); break;
    case MT_TIMEOUT:  tag(s, C_RED,    "[  TIMEOUT ]"); break;
    }
    fprintf(s->out, " %s.%s (%.2f ms)", t->suite, t->name, ms(r->seconds));
    if (r->detail && *r->detail)
        fprintf(s->out, ": %s", r->detail);
    fputc('\n', s->out);

    for (const mt_failure *f = r->failures; f; f = f->next)
        fprintf(s->out, "  %s:%d: %s\n", f->file, f->line, f->message);
}

static int con_end(void *state, const mt_result *results, size_t n,
                   const mt_summary *sum)
{
    console_state *s = state;
    tag(s, C_GREEN, "[==========]");
    fprintf(s->out, " %zu test%s ran (%.2f ms total)\n",
            sum->total, sum->total == 1 ? "" : "s", ms(sum->seconds));

    tag(s, C_GREEN, "[  PASSED  ]");
    fprintf(s->out, " %zu\n", sum->passed);
    if (sum->skipped) {
        tag(s, C_YELLOW, "[  SKIPPED ]");
        fprintf(s->out, " %zu\n", sum->skipped);
    }

    size_t bad = sum->failed + sum->errored;
    if (bad) {
        tag(s, C_RED, "[  FAILED  ]");
        fprintf(s->out, " %zu, listed below:\n", bad);
        for (size_t i = 0; i < n; i++) {
            if (!mt_status_is_bad(results[i].status))
                continue;
            fprintf(s->out, "    %s.%s (%s)\n", results[i].test->suite,
                    results[i].test->name, mt_status_name(results[i].status));
        }
        if (sum->seed)
            fprintf(s->out, "Reproduce this order with --seed=%llu\n",
                    (unsigned long long)sum->seed);
    }
    fflush(s->out);
    return 0;
}

static void con_destroy(void *state) { free(state); }

int mt_console_reporter(mt_reporter *rep, FILE *out, int color, int verbose)
{
    console_state *s = malloc(sizeof *s);
    if (!s)
        return -1;
    s->out = out;
    /* Auto mode honours https://no-color.org and only colours terminals. */
    s->color = color >= 0 ? color : (!getenv("NO_COLOR") && isatty(fileno(out)));
    s->verbose = verbose;

    rep->state = s;
    rep->begin = con_begin;
    rep->test_start = con_test_start;
    rep->test_done = con_test_done;
    rep->end = con_end;
    rep->destroy = con_destroy;
    return 0;
}
