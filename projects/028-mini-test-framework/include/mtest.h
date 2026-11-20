/*
 * mtest — a small xUnit-style test framework for C11.
 *
 * Public API. Test files include only this header and link against
 * libmtest.a plus mtest_main.o (which supplies main()).
 *
 *   TEST(suite, name) { ... }           a plain test
 *   FIXTURE(type) { fields };           a fixture struct, plus
 *   FIXTURE_SETUP(type) { self->... }   its setup and
 *   FIXTURE_TEARDOWN(type) { ... }      teardown (both required)
 *   TEST_F(type, name) { self->... }    a test that receives a fresh fixture
 *
 * EXPECT_* records a failure and keeps going; ASSERT_* records a failure and
 * ends the current test immediately. Every macro evaluates its arguments
 * exactly once, so `ASSERT_EQ_INT(next(&it), 3)` is safe.
 *
 * Tests self-register via a constructor function (GCC/Clang
 * `__attribute__((constructor))`), so there is no hand-maintained list.
 */
#ifndef MTEST_H
#define MTEST_H

#include <stddef.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#if !defined(__GNUC__) && !defined(__clang__)
#error "mtest needs GCC or Clang (it relies on __attribute__((constructor)))"
#endif

/* ---- Registration ---------------------------------------------------- */

typedef struct mt_fixture_def {
    size_t size;                    /* sizeof the fixture struct */
    void (*setup)(void *self);
    void (*teardown)(void *self);
} mt_fixture_def;

typedef struct mt_test {
    const char *suite;
    const char *name;
    const char *file;
    int line;
    void (*fn)(void *fixture);      /* fixture is NULL for plain TESTs */
    const mt_fixture_def *fixture;  /* NULL for plain TESTs */
    struct mt_test *next;           /* intrusive registry link */
} mt_test;

/* Called by the constructor that each TEST/TEST_F expands into. */
void mt_register(mt_test *test);

/* Entry point: parses argv, runs the selected tests, returns an exit code
 * (0 = everything passed or was skipped, 1 = failures, 2 = usage error). */
int mt_main(int argc, char **argv);

/* ---- Assertion back-end (used by the macros) ------------------------- */

/* Records a failure on the running test. When `fatal` is non-zero this
 * does not return: control jumps back to the runner. */
void mt_fail(const char *file, int line, int fatal, const char *fmt, ...)
    __attribute__((format(printf, 4, 5)));

/* Marks the running test as skipped and ends it. Never returns. */
void mt_skip(const char *file, int line, const char *reason)
    __attribute__((noreturn));

/* ---- Test definition macros ----------------------------------------- */

#define MT_CAT_(a, b) a##b
#define MT_CAT(a, b) MT_CAT_(a, b)
/* Unique per-test identifier, e.g. mt_body_stack__push_pop. */
#define MT_ID(suite, name, part) mt_##part##_##suite##__##name

#define MT_DEFINE_TEST_(suite, name, fixture_def, body_param)                 \
    static void MT_ID(suite, name, body)(body_param);                         \
    static void MT_ID(suite, name, thunk)(void *mt_fx_)                       \
    {                                                                         \
        MT_ID(suite, name, body)(mt_fx_);                                     \
    }                                                                         \
    static mt_test MT_ID(suite, name, rec) = {                                \
        #suite, #name, __FILE__, __LINE__,                                    \
        MT_ID(suite, name, thunk), (fixture_def), NULL};                      \
    __attribute__((constructor)) static void MT_ID(suite, name, reg)(void)    \
    {                                                                         \
        mt_register(&MT_ID(suite, name, rec));                                \
    }                                                                         \
    static void MT_ID(suite, name, body)(body_param)

#define TEST(suite, name) \
    MT_DEFINE_TEST_(suite, name, NULL, __attribute__((unused)) void *mt_unused_)

/* FIXTURE(T) declares the struct T and the thunks that adapt T-typed setup
 * and teardown to the void* signature the runner calls. */
#define FIXTURE(type)                                                         \
    typedef struct type type;                                                 \
    static void MT_CAT(type, _mt_setup)(type *self);                          \
    static void MT_CAT(type, _mt_teardown)(type *self);                       \
    __attribute__((unused)) static void MT_CAT(type, _mt_setup_thunk)(void *p) \
    {                                                                         \
        MT_CAT(type, _mt_setup)((type *)p);                                   \
    }                                                                         \
    __attribute__((unused)) static void MT_CAT(type, _mt_teardown_thunk)(void *p) \
    {                                                                         \
        MT_CAT(type, _mt_teardown)((type *)p);                                \
    }                                                                         \
    struct type

#define FIXTURE_SETUP(type) static void MT_CAT(type, _mt_setup)(type *self)
#define FIXTURE_TEARDOWN(type) \
    static void MT_CAT(type, _mt_teardown)(__attribute__((unused)) type *self)

#define TEST_F(type, name)                                                    \
    static const mt_fixture_def MT_ID(type, name, fdef) = {                   \
        sizeof(type), MT_CAT(type, _mt_setup_thunk),                          \
        MT_CAT(type, _mt_teardown_thunk)};                                    \
    MT_DEFINE_TEST_(type, name, &MT_ID(type, name, fdef), type *self)

/* ---- Assertions ------------------------------------------------------ */

#define MT_BOOL_(fatal, cond, expect)                                         \
    do {                                                                      \
        if ((!!(cond)) != (expect))                                           \
            mt_fail(__FILE__, __LINE__, fatal, "expected %s to be %s",        \
                    #cond, (expect) ? "true" : "false");                      \
    } while (0)

#define MT_CMP_INT_(fatal, a, op, b)                                          \
    do {                                                                      \
        long long mt_a_ = (long long)(a), mt_b_ = (long long)(b);             \
        if (!(mt_a_ op mt_b_))                                                \
            mt_fail(__FILE__, __LINE__, fatal,                                \
                    "expected %s %s %s\n    left:  %lld\n    right: %lld",    \
                    #a, #op, #b, mt_a_, mt_b_);                               \
    } while (0)

#define MT_CMP_UINT_(fatal, a, op, b)                                         \
    do {                                                                      \
        unsigned long long mt_a_ = (unsigned long long)(a);                   \
        unsigned long long mt_b_ = (unsigned long long)(b);                   \
        if (!(mt_a_ op mt_b_))                                                \
            mt_fail(__FILE__, __LINE__, fatal,                                \
                    "expected %s %s %s\n    left:  %llu\n    right: %llu",    \
                    #a, #op, #b, mt_a_, mt_b_);                               \
    } while (0)

#define MT_STR_(fatal, a, b, want_equal)                                      \
    do {                                                                      \
        const char *mt_a_ = (a), *mt_b_ = (b);                                \
        int mt_eq_ = (mt_a_ == mt_b_) ||                                      \
                     (mt_a_ && mt_b_ && strcmp(mt_a_, mt_b_) == 0);           \
        if (mt_eq_ != (want_equal))                                           \
            mt_fail(__FILE__, __LINE__, fatal,                                \
                    "expected %s %s %s\n    left:  %s%s%s\n    right: %s%s%s", \
                    #a, (want_equal) ? "==" : "!=", #b,                       \
                    mt_a_ ? "\"" : "", mt_a_ ? mt_a_ : "NULL",                \
                    mt_a_ ? "\"" : "", mt_b_ ? "\"" : "",                     \
                    mt_b_ ? mt_b_ : "NULL", mt_b_ ? "\"" : "");               \
    } while (0)

#define MT_NEAR_(fatal, a, b, eps)                                            \
    do {                                                                      \
        double mt_a_ = (a), mt_b_ = (b), mt_e_ = (eps);                       \
        double mt_d_ = mt_a_ > mt_b_ ? mt_a_ - mt_b_ : mt_b_ - mt_a_;         \
        if (!(mt_d_ <= mt_e_))                                                \
            mt_fail(__FILE__, __LINE__, fatal,                                \
                    "expected %s within %g of %s\n    left:  %.17g\n"         \
                    "    right: %.17g\n    diff:  %.17g",                     \
                    #a, mt_e_, #b, mt_a_, mt_b_, mt_d_);                      \
    } while (0)

#define MT_PTR_(fatal, p, want_null)                                          \
    do {                                                                      \
        const void *mt_p_ = (const void *)(p);                                \
        if ((mt_p_ == NULL) != (want_null))                                   \
            mt_fail(__FILE__, __LINE__, fatal, "expected %s to be %s (got %p)", \
                    #p, (want_null) ? "NULL" : "non-NULL", mt_p_);            \
    } while (0)

#define MT_MEM_(fatal, a, b, n)                                               \
    do {                                                                      \
        const unsigned char *mt_a_ = (const unsigned char *)(a);              \
        const unsigned char *mt_b_ = (const unsigned char *)(b);              \
        size_t mt_n_ = (n), mt_i_;                                            \
        for (mt_i_ = 0; mt_i_ < mt_n_ && mt_a_[mt_i_] == mt_b_[mt_i_]; mt_i_++) \
            ;                                                                 \
        if (mt_i_ < mt_n_)                                                    \
            mt_fail(__FILE__, __LINE__, fatal,                                \
                    "expected %s and %s to match for %zu bytes\n"             \
                    "    first difference at offset %zu: 0x%02x vs 0x%02x",   \
                    #a, #b, mt_n_, mt_i_, mt_a_[mt_i_], mt_b_[mt_i_]);        \
    } while (0)

#define ASSERT_TRUE(c)  MT_BOOL_(1, c, 1)
#define ASSERT_FALSE(c) MT_BOOL_(1, c, 0)
#define EXPECT_TRUE(c)  MT_BOOL_(0, c, 1)
#define EXPECT_FALSE(c) MT_BOOL_(0, c, 0)

#define ASSERT_EQ_INT(a, b) MT_CMP_INT_(1, a, ==, b)
#define ASSERT_NE_INT(a, b) MT_CMP_INT_(1, a, !=, b)
#define ASSERT_LT_INT(a, b) MT_CMP_INT_(1, a, <, b)
#define ASSERT_LE_INT(a, b) MT_CMP_INT_(1, a, <=, b)
#define ASSERT_GT_INT(a, b) MT_CMP_INT_(1, a, >, b)
#define ASSERT_GE_INT(a, b) MT_CMP_INT_(1, a, >=, b)
#define EXPECT_EQ_INT(a, b) MT_CMP_INT_(0, a, ==, b)
#define EXPECT_NE_INT(a, b) MT_CMP_INT_(0, a, !=, b)
#define EXPECT_LT_INT(a, b) MT_CMP_INT_(0, a, <, b)
#define EXPECT_LE_INT(a, b) MT_CMP_INT_(0, a, <=, b)
#define EXPECT_GT_INT(a, b) MT_CMP_INT_(0, a, >, b)
#define EXPECT_GE_INT(a, b) MT_CMP_INT_(0, a, >=, b)

#define ASSERT_EQ_UINT(a, b) MT_CMP_UINT_(1, a, ==, b)
#define ASSERT_NE_UINT(a, b) MT_CMP_UINT_(1, a, !=, b)
#define EXPECT_EQ_UINT(a, b) MT_CMP_UINT_(0, a, ==, b)
#define EXPECT_NE_UINT(a, b) MT_CMP_UINT_(0, a, !=, b)

#define ASSERT_STREQ(a, b) MT_STR_(1, a, b, 1)
#define ASSERT_STRNE(a, b) MT_STR_(1, a, b, 0)
#define EXPECT_STREQ(a, b) MT_STR_(0, a, b, 1)
#define EXPECT_STRNE(a, b) MT_STR_(0, a, b, 0)

#define ASSERT_NEAR(a, b, eps) MT_NEAR_(1, a, b, eps)
#define EXPECT_NEAR(a, b, eps) MT_NEAR_(0, a, b, eps)

#define ASSERT_NULL(p)     MT_PTR_(1, p, 1)
#define ASSERT_NOT_NULL(p) MT_PTR_(1, p, 0)
#define EXPECT_NULL(p)     MT_PTR_(0, p, 1)
#define EXPECT_NOT_NULL(p) MT_PTR_(0, p, 0)

#define ASSERT_MEMEQ(a, b, n) MT_MEM_(1, a, b, n)
#define EXPECT_MEMEQ(a, b, n) MT_MEM_(0, a, b, n)

/* Unconditional failure with a printf-style message. */
#define FAIL(...) mt_fail(__FILE__, __LINE__, 1, __VA_ARGS__)
#define ADD_FAILURE(...) mt_fail(__FILE__, __LINE__, 0, __VA_ARGS__)

/* Ends the test as skipped (not counted as a failure). */
#define SKIP(reason) mt_skip(__FILE__, __LINE__, (reason))

#ifdef __cplusplus
}
#endif

#endif /* MTEST_H */
