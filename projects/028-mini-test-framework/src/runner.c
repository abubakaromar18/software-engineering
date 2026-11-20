/*
 * Executes a single test: fixture setup -> body -> teardown, either in this
 * process or in a forked child that reports back over a pipe.
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#include "internal.h"

/* Child exit codes. Anything else means the test escaped the runner. */
enum { EXIT_PASSED = 0, EXIT_FAILED = 1, EXIT_SKIPPED = 2 };

static char *format(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static char *format(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    char *s = mt_vformat(fmt, ap);
    va_end(ap);
    return s;
}

/*
 * The xUnit life cycle. Fatal assertions longjmp back to the setjmp that is
 * active at the time, so setup+body and teardown each get their own landing
 * point. Teardown runs whenever setup completed, even if the body failed,
 * so fixtures can always release what setup acquired.
 *
 * Kept in its own function so that nothing it reads after a longjmp is a
 * local that could have been modified since setjmp (C11 7.13.2.1).
 */
static void run_phases(const mt_test *t, mt_context *ctx, void *fx)
{
    /* Written between setjmp and a possible longjmp, so must be volatile. */
    volatile int setup_done = 0;

    if (setjmp(ctx->jump) == 0) {
        if (t->fixture)
            t->fixture->setup(fx);
        setup_done = 1;
        t->fn(fx);
    }
    if (t->fixture && setup_done) {
        if (setjmp(ctx->jump) == 0)
            t->fixture->teardown(fx);
    }
}

static void execute(const mt_test *t, mt_result *r, int report_fd)
{
    void *fx = NULL;
    if (t->fixture) {
        fx = calloc(1, t->fixture->size ? t->fixture->size : 1);
        if (!fx) {
            mt_result_add_failure(r, t->file, t->line, "could not allocate fixture");
            r->status = MT_FAIL;
            return;
        }
    }

    mt_context ctx;
    memset(&ctx, 0, sizeof ctx);
    ctx.result = r;
    ctx.report_fd = report_fd;

    mt_context_enter(&ctx);
    run_phases(t, &ctx, fx);
    mt_context_leave();
    free(fx);
}

static void run_in_process(const mt_test *t, mt_result *r)
{
    execute(t, r, -1);
}

static void run_in_child(const mt_test *t, const mt_options *opts, int fd)
{
    if (opts->timeout_secs)
        alarm(opts->timeout_secs);   /* default SIGALRM action kills us */

    mt_result local;
    memset(&local, 0, sizeof local);
    local.test = t;
    local.status = MT_PASS;
    execute(t, &local, fd);
    mt_record_write(fd, MT_REC_DONE, "", 0, "");

    int code = local.status == MT_SKIP ? EXIT_SKIPPED
             : local.status == MT_PASS ? EXIT_PASSED : EXIT_FAILED;
    fflush(NULL);
    _exit(code);   /* skip atexit handlers inherited from the parent */
}

static void run_forked(const mt_test *t, const mt_options *opts, mt_result *r)
{
    int fds[2];
    if (pipe(fds) != 0) {
        r->status = MT_CRASH;
        r->detail = format("pipe failed: %s", strerror(errno));
        return;
    }

    fflush(NULL);   /* otherwise buffered output would be printed twice */
    pid_t pid = fork();
    if (pid < 0) {
        r->status = MT_CRASH;
        r->detail = format("fork failed: %s", strerror(errno));
        close(fds[0]);
        close(fds[1]);
        return;
    }
    if (pid == 0) {
        close(fds[0]);
        run_in_child(t, opts, fds[1]);
    }

    close(fds[1]);
    int done = 0;
    int stream_ok = mt_record_read_all(fds[0], r, &done) == 0;
    close(fds[0]);

    int status;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR) {
            r->status = MT_CRASH;
            r->detail = format("waitpid failed: %s", strerror(errno));
            return;
        }
    }

    if (WIFSIGNALED(status)) {
        int sig = WTERMSIG(status);
        if (sig == SIGALRM && opts->timeout_secs) {
            r->status = MT_TIMEOUT;
            r->detail = format("exceeded %us timeout", opts->timeout_secs);
        } else {
            r->status = MT_CRASH;
            r->detail = format("killed by signal %d (%s)", sig, strsignal(sig));
        }
    } else if (!done || !stream_ok) {
        /* The test called exit() itself, or corrupted the report stream. */
        r->status = MT_CRASH;
        r->detail = format("test exited early with status %d", WEXITSTATUS(status));
    } else {
        switch (WEXITSTATUS(status)) {
        case EXIT_PASSED:  r->status = MT_PASS; break;
        case EXIT_FAILED:  r->status = MT_FAIL; break;
        case EXIT_SKIPPED: r->status = MT_SKIP; break;
        default:
            r->status = MT_CRASH;
            r->detail = format("unexpected exit status %d", WEXITSTATUS(status));
        }
    }
}

void mt_run_one(const mt_test *test, const mt_options *opts, mt_result *out)
{
    memset(out, 0, sizeof *out);
    out->test = test;
    out->status = MT_PASS;

    double start = mt_now_seconds();
    if (opts->use_fork)
        run_forked(test, opts, out);
    else
        run_in_process(test, out);
    out->seconds = mt_now_seconds() - start;
}
