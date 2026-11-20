/*
 * Assertion back-end. The running test's context is a global stack: tests
 * run one at a time, but the framework's own self-tests run tests *inside*
 * a test, so entering a context saves the outer one and leaving restores it.
 * In fork mode each child has its own copy.
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "internal.h"

static mt_context *g_ctx;

void mt_context_enter(mt_context *ctx)
{
    ctx->prev = g_ctx;
    g_ctx = ctx;
}

void mt_context_leave(void)
{
    if (g_ctx)
        g_ctx = g_ctx->prev;
}

static mt_context *require_context(const char *what, const char *file, int line)
{
    if (!g_ctx) {
        fprintf(stderr, "%s:%d: %s used outside a running test\n", file, line, what);
        abort();
    }
    return g_ctx;
}

void mt_fail(const char *file, int line, int fatal, const char *fmt, ...)
{
    mt_context *ctx = require_context("assertion", file, line);

    va_list ap;
    va_start(ap, fmt);
    char *msg = mt_vformat(fmt, ap);
    va_end(ap);

    /* In a child, stream the record now so it survives a later crash. */
    if (ctx->report_fd >= 0)
        mt_record_write(ctx->report_fd, MT_REC_FAILURE, file, line, msg);
    mt_result_add_failure(ctx->result, file, line, msg);
    ctx->result->status = MT_FAIL;
    free(msg);

    if (fatal)
        longjmp(ctx->jump, 1);
}

void mt_skip(const char *file, int line, const char *reason)
{
    mt_context *ctx = require_context("SKIP", file, line);
    const char *why = reason ? reason : "";

    if (ctx->report_fd >= 0)
        mt_record_write(ctx->report_fd, MT_REC_SKIP, file, line, why);
    /* A skip after a recorded failure keeps the failure: skipping must
     * never hide a problem. */
    if (ctx->result->status != MT_FAIL) {
        ctx->result->status = MT_SKIP;
        free(ctx->result->detail);
        ctx->result->detail = mt_strdup(why);
    }
    longjmp(ctx->jump, 1);
}

/* ---- Child -> parent record stream ------------------------------------
 * Each record: kind (1 byte), line (int32), file length (uint32), message
 * length (uint32), then the two strings without terminators. Native byte
 * order is fine: both ends are the same process image. */

static int write_all(int fd, const void *buf, size_t n)
{
    const char *p = buf;
    while (n > 0) {
        ssize_t w = write(fd, p, n);
        if (w < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        p += w;
        n -= (size_t)w;
    }
    return 0;
}

/* Returns 1 on success, 0 on clean EOF before any byte, -1 on error/short. */
static int read_all(int fd, void *buf, size_t n)
{
    char *p = buf;
    size_t got = 0;
    while (got < n) {
        ssize_t r = read(fd, p + got, n - got);
        if (r < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        if (r == 0)
            return got == 0 ? 0 : -1;
        got += (size_t)r;
    }
    return 1;
}

int mt_record_write(int fd, char kind, const char *file, int line, const char *msg)
{
    uint32_t flen = (uint32_t)strlen(file), mlen = (uint32_t)strlen(msg);
    int32_t l = line;
    if (write_all(fd, &kind, 1) || write_all(fd, &l, sizeof l) ||
        write_all(fd, &flen, sizeof flen) || write_all(fd, &mlen, sizeof mlen) ||
        write_all(fd, file, flen) || write_all(fd, msg, mlen))
        return -1;
    return 0;
}

int mt_record_read_all(int fd, mt_result *r, int *done)
{
    *done = 0;
    for (;;) {
        char kind;
        int rc = read_all(fd, &kind, 1);
        if (rc == 0)
            return 0;                     /* clean end of stream */
        if (rc < 0)
            return -1;

        int32_t line;
        uint32_t flen, mlen;
        if (read_all(fd, &line, sizeof line) != 1 ||
            read_all(fd, &flen, sizeof flen) != 1 ||
            read_all(fd, &mlen, sizeof mlen) != 1)
            return -1;

        char *file = malloc((size_t)flen + 1), *msg = malloc((size_t)mlen + 1);
        if (!file || !msg || (flen && read_all(fd, file, flen) != 1) ||
            (mlen && read_all(fd, msg, mlen) != 1)) {
            free(file);
            free(msg);
            return -1;
        }
        file[flen] = '\0';
        msg[mlen] = '\0';

        if (kind == MT_REC_FAILURE) {
            mt_result_add_failure(r, file, line, msg);
        } else if (kind == MT_REC_SKIP) {
            free(r->detail);
            r->detail = msg;
            msg = NULL;
        } else if (kind == MT_REC_DONE) {
            *done = 1;
        }
        free(file);
        free(msg);
    }
}
