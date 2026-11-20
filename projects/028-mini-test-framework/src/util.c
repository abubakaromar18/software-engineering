/* Small allocation, formatting and clock helpers, plus mt_result upkeep. */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "internal.h"

static void *xmalloc(size_t n)
{
    void *p = malloc(n);
    if (!p) {
        fputs("mtest: out of memory\n", stderr);
        abort();
    }
    return p;
}

char *mt_strdup(const char *s)
{
    size_t n = strlen(s) + 1;
    return memcpy(xmalloc(n), s, n);
}

char *mt_vformat(const char *fmt, va_list ap)
{
    if (!fmt)
        return mt_strdup("");
    va_list copy;
    va_copy(copy, ap);
    int n = vsnprintf(NULL, 0, fmt, copy);
    va_end(copy);
    if (n < 0)
        return mt_strdup("(unformattable message)");
    char *buf = xmalloc((size_t)n + 1);
    vsnprintf(buf, (size_t)n + 1, fmt, ap);
    return buf;
}

double mt_now_seconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

const char *mt_status_name(mt_status status)
{
    switch (status) {
    case MT_PASS:    return "passed";
    case MT_FAIL:    return "failed";
    case MT_SKIP:    return "skipped";
    case MT_CRASH:   return "crashed";
    case MT_TIMEOUT: return "timed out";
    }
    return "unknown";
}

int mt_status_is_bad(mt_status status)
{
    return status == MT_FAIL || status == MT_CRASH || status == MT_TIMEOUT;
}

void mt_result_add_failure(mt_result *r, const char *file, int line, const char *msg)
{
    mt_failure *f = xmalloc(sizeof *f);
    f->file = mt_strdup(file);
    f->line = line;
    f->message = mt_strdup(msg);
    f->next = NULL;

    mt_failure **tail = &r->failures;   /* append keeps recording order */
    while (*tail)
        tail = &(*tail)->next;
    *tail = f;
}

void mt_result_free(mt_result *r)
{
    mt_failure *f = r->failures;
    while (f) {
        mt_failure *next = f->next;
        free(f->file);
        free(f->message);
        free(f);
        f = next;
    }
    free(r->detail);
    r->failures = NULL;
    r->detail = NULL;
}
