/* Unit tests for the XML escaping used by the JUnit reporter. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>

#include "internal.h"

/* Escapes s into a heap string via an in-memory FILE. */
static char *escaped(const char *s)
{
    char *buf = NULL;
    size_t len = 0;
    FILE *f = open_memstream(&buf, &len);
    if (!f)
        return NULL;
    mt_xml_escape(f, s);
    fclose(f);
    return buf;
}

TEST(xml, escapes_markup_characters)
{
    char *s = escaped("a < b && \"c\" > 'd'");
    ASSERT_NOT_NULL(s);
    EXPECT_STREQ(s, "a &lt; b &amp;&amp; &quot;c&quot; &gt; &apos;d&apos;");
    free(s);
}

TEST(xml, keeps_whitespace_and_utf8)
{
    char *s = escaped("line1\n\tcaf\xc3\xa9");
    ASSERT_NOT_NULL(s);
    EXPECT_STREQ(s, "line1\n\tcaf\xc3\xa9");
    free(s);
}

TEST(xml, neutralises_illegal_control_characters)
{
    char *s = escaped("bell\x07!");
    ASSERT_NOT_NULL(s);
    EXPECT_STREQ(s, "bell\\x07!");
    free(s);
}
