/* Global test registry populated by constructors before main() runs. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "internal.h"

/* An intrusive singly linked list: registration never allocates, which
 * matters because it runs before main() where failure handling is awkward. */
static mt_test *g_head;

void mt_register(mt_test *test)
{
    test->next = g_head;
    g_head = test;
}

/* Constructor order is unspecified across translation units, so sort by
 * source location to get the same order on every compiler and link. */
static int by_location(const void *a, const void *b)
{
    const mt_test *x = *(mt_test *const *)a;
    const mt_test *y = *(mt_test *const *)b;
    int c = strcmp(x->file, y->file);
    if (c)
        return c;
    return (x->line > y->line) - (x->line < y->line);
}

mt_test **mt_registry_select(const char *filter, size_t *count)
{
    size_t total = 0;
    for (mt_test *t = g_head; t; t = t->next)
        total++;

    mt_test **out = malloc((total ? total : 1) * sizeof *out);
    if (!out) {
        *count = 0;
        return NULL;
    }

    size_t n = 0;
    char name[512];
    for (mt_test *t = g_head; t; t = t->next) {
        snprintf(name, sizeof name, "%s.%s", t->suite, t->name);
        if (mt_filter_match(filter, name))
            out[n++] = t;
    }
    qsort(out, n, sizeof *out, by_location);
    *count = n;
    return out;
}

/* splitmix64: tiny, well-distributed, and identical on every platform,
 * so a printed seed reproduces the same order anywhere. */
static uint64_t splitmix64(uint64_t *state)
{
    uint64_t z = (*state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

void mt_shuffle(mt_test **tests, size_t count, uint64_t seed)
{
    uint64_t state = seed;
    for (size_t i = count; i > 1; i--) {
        size_t j = (size_t)(splitmix64(&state) % i);   /* bias negligible here */
        mt_test *tmp = tests[i - 1];
        tests[i - 1] = tests[j];
        tests[j] = tmp;
    }
}
