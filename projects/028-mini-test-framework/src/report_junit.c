/*
 * JUnit XML report, the de-facto interchange format that CI systems
 * (GitHub Actions, GitLab, Jenkins) render natively. Everything is written
 * in end(), once all results exist, grouped into one <testsuite> per suite.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "internal.h"

typedef struct {
    char *path;
} junit_state;

void mt_xml_escape(FILE *out, const char *s)
{
    for (const unsigned char *p = (const unsigned char *)s; *p; p++) {
        switch (*p) {
        case '&':  fputs("&amp;", out); break;
        case '<':  fputs("&lt;", out); break;
        case '>':  fputs("&gt;", out); break;
        case '"':  fputs("&quot;", out); break;
        case '\'': fputs("&apos;", out); break;
        case '\n': case '\t': case '\r':
            fputc(*p, out);
            break;
        default:
            /* Other C0 control characters are illegal in XML 1.0. */
            if (*p < 0x20)
                fprintf(out, "\\x%02x", *p);
            else
                fputc(*p, out);
        }
    }
}

/* Every recorded assertion, one "file:line: message" per line. */
static void write_failures(FILE *out, const mt_result *r)
{
    for (const mt_failure *f = r->failures; f; f = f->next) {
        mt_xml_escape(out, f->file);
        fprintf(out, ":%d: ", f->line);
        mt_xml_escape(out, f->message);
        fputc('\n', out);
    }
}

static void write_case(FILE *out, const mt_result *r)
{
    const mt_test *t = r->test;
    fputs("    <testcase classname=\"", out);
    mt_xml_escape(out, t->suite);
    fputs("\" name=\"", out);
    mt_xml_escape(out, t->name);
    fputs("\" file=\"", out);
    mt_xml_escape(out, t->file);
    fprintf(out, "\" line=\"%d\" time=\"%.6f\"", t->line, r->seconds);

    if (r->status == MT_PASS) {
        fputs("/>\n", out);
        return;
    }
    fputs(">\n", out);

    if (r->status == MT_SKIP) {
        fputs("      <skipped message=\"", out);
        mt_xml_escape(out, r->detail ? r->detail : "");
        fputs("\"/>\n", out);
    } else if (r->status == MT_FAIL) {
        /* One <failure> per test; every recorded assertion goes in its body. */
        const char *first = r->failures ? r->failures->message : "failed";
        const char *nl = strchr(first, '\n');
        fputs("      <failure message=\"", out);
        if (nl) {
            char *head = malloc((size_t)(nl - first) + 1);
            if (head) {
                memcpy(head, first, (size_t)(nl - first));
                head[nl - first] = '\0';
                mt_xml_escape(out, head);
                free(head);
            }
        } else {
            mt_xml_escape(out, first);
        }
        fputs("\">", out);
        write_failures(out, r);
        fputs("</failure>\n", out);
    } else {
        /* Crashes and timeouts are errors (the test could not finish),
         * which JUnit distinguishes from assertion failures. */
        fprintf(out, "      <error type=\"%s\" message=\"", mt_status_name(r->status));
        mt_xml_escape(out, r->detail ? r->detail : "");
        fputs("\">", out);
        write_failures(out, r);
        fputs("</error>\n", out);
    }
    fputs("    </testcase>\n", out);
}

static int junit_end(void *state, const mt_result *results, size_t n,
                     const mt_summary *sum)
{
    junit_state *s = state;
    FILE *out = fopen(s->path, "w");
    if (!out) {
        fprintf(stderr, "mtest: cannot write JUnit report to '%s'\n", s->path);
        return -1;
    }

    fputs("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n", out);
    fprintf(out, "<testsuites tests=\"%zu\" failures=\"%zu\" errors=\"%zu\" "
                 "skipped=\"%zu\" time=\"%.6f\">\n",
            sum->total, sum->failed, sum->errored, sum->skipped, sum->seconds);

    /* Group by suite without reordering: a suite's block starts at its
     * first result, and a done[] mask stops it being emitted twice. */
    char *done = calloc(n ? n : 1, 1);
    if (!done) {
        fclose(out);
        return -1;
    }
    for (size_t i = 0; i < n; i++) {
        if (done[i])
            continue;
        const char *suite = results[i].test->suite;
        size_t tests = 0, failures = 0, errors = 0, skipped = 0;
        double time = 0;
        for (size_t j = i; j < n; j++) {
            if (strcmp(results[j].test->suite, suite) != 0)
                continue;
            tests++;
            time += results[j].seconds;
            failures += results[j].status == MT_FAIL;
            skipped += results[j].status == MT_SKIP;
            errors += results[j].status == MT_CRASH || results[j].status == MT_TIMEOUT;
        }
        fputs("  <testsuite name=\"", out);
        mt_xml_escape(out, suite);
        fprintf(out, "\" tests=\"%zu\" failures=\"%zu\" errors=\"%zu\" "
                     "skipped=\"%zu\" time=\"%.6f\">\n",
                tests, failures, errors, skipped, time);
        for (size_t j = i; j < n; j++) {
            if (!done[j] && strcmp(results[j].test->suite, suite) == 0) {
                write_case(out, &results[j]);
                done[j] = 1;
            }
        }
        fputs("  </testsuite>\n", out);
    }
    free(done);
    fputs("</testsuites>\n", out);

    if (fclose(out) != 0) {
        fprintf(stderr, "mtest: error writing JUnit report '%s'\n", s->path);
        return -1;
    }
    return 0;
}

static void junit_destroy(void *state)
{
    junit_state *s = state;
    free(s->path);
    free(s);
}

int mt_junit_reporter(mt_reporter *rep, const char *path)
{
    junit_state *s = malloc(sizeof *s);
    if (!s)
        return -1;
    s->path = mt_strdup(path);

    memset(rep, 0, sizeof *rep);   /* only end() and destroy() are needed */
    rep->state = s;
    rep->end = junit_end;
    rep->destroy = junit_destroy;
    return 0;
}
