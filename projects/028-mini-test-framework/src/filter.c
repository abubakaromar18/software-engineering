/* Test selection: glob matching and comma-separated filter expressions. */
#include <string.h>

#include "internal.h"

/*
 * Iterative glob matcher with single-star backtracking. When a '*' is seen
 * we remember where it was and how much text it has absorbed; on a later
 * mismatch we let the star absorb one more character and retry. This is
 * O(|pattern| * |text|) worst case with no recursion or allocation.
 */
int mt_glob_match(const char *pattern, const char *text)
{
    const char *p = pattern, *t = text;
    const char *star = NULL, *star_text = NULL;

    while (*t) {
        if (*p == '*') {
            star = p++;
            star_text = t;
        } else if (*p == '?' || *p == *t) {
            p++;
            t++;
        } else if (star) {
            p = star + 1;
            t = ++star_text;
        } else {
            return 0;
        }
    }
    while (*p == '*')
        p++;
    return *p == '\0';
}

/* Matches one comma-delimited token [start, start+len) against name. */
static int token_match(const char *start, size_t len, const char *name)
{
    char buf[256];
    if (len >= sizeof buf)
        len = sizeof buf - 1;   /* absurdly long patterns are truncated */
    memcpy(buf, start, len);
    buf[len] = '\0';
    return mt_glob_match(buf, name);
}

int mt_filter_match(const char *filter, const char *full_name)
{
    if (!filter || !*filter)
        return 1;

    int saw_positive = 0, positive_hit = 0;
    const char *s = filter;
    while (*s) {
        const char *end = strchr(s, ',');
        size_t len = end ? (size_t)(end - s) : strlen(s);
        if (len > 0) {
            if (*s == '-') {
                if (len > 1 && token_match(s + 1, len - 1, full_name))
                    return 0;            /* exclusions always win */
            } else {
                saw_positive = 1;
                if (token_match(s, len, full_name))
                    positive_hit = 1;
            }
        }
        if (!end)
            break;
        s = end + 1;
    }
    return saw_positive ? positive_hit : 1;
}
