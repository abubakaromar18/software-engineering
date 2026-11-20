/* Example suite: how a project uses mtest, fixtures included. */
#include "mtest.h"
#include "ringbuf.h"

TEST(ringbuf, rejects_zero_capacity)
{
    EXPECT_NULL(ringbuf_new(0));
}

TEST(ringbuf, new_buffer_is_empty)
{
    ringbuf *rb = ringbuf_new(4);
    ASSERT_NOT_NULL(rb);   /* fatal: nothing below makes sense without it */
    EXPECT_TRUE(ringbuf_is_empty(rb));
    EXPECT_FALSE(ringbuf_is_full(rb));
    EXPECT_EQ_UINT(ringbuf_capacity(rb), 4);
    ringbuf_free(rb);
}

/* A fixture gives every TEST_F a freshly built three-slot buffer, and its
 * teardown frees it even when an ASSERT ends the test early. */
FIXTURE(rb3) {
    ringbuf *rb;
};

FIXTURE_SETUP(rb3)
{
    self->rb = ringbuf_new(3);
    ASSERT_NOT_NULL(self->rb);
}

FIXTURE_TEARDOWN(rb3)
{
    ringbuf_free(self->rb);
}

TEST_F(rb3, pops_in_fifo_order)
{
    for (int i = 1; i <= 3; i++)
        ASSERT_TRUE(ringbuf_push(self->rb, i * 10));

    int v;
    for (int i = 1; i <= 3; i++) {
        ASSERT_TRUE(ringbuf_pop(self->rb, &v));
        EXPECT_EQ_INT(v, i * 10);
    }
    EXPECT_FALSE(ringbuf_pop(self->rb, &v));
}

TEST_F(rb3, push_fails_when_full)
{
    for (int i = 0; i < 3; i++)
        ASSERT_TRUE(ringbuf_push(self->rb, i));
    EXPECT_TRUE(ringbuf_is_full(self->rb));
    EXPECT_FALSE(ringbuf_push(self->rb, 99));
    EXPECT_EQ_UINT(ringbuf_len(self->rb), 3);
}

TEST_F(rb3, wraps_around_the_end)
{
    int v;
    /* Advance head so later pushes wrap past the last slot. */
    for (int round = 0; round < 5; round++) {
        ASSERT_TRUE(ringbuf_push(self->rb, round));
        ASSERT_TRUE(ringbuf_push(self->rb, round + 100));
        ASSERT_TRUE(ringbuf_pop(self->rb, &v));
        EXPECT_EQ_INT(v, round);
        ASSERT_TRUE(ringbuf_pop(self->rb, &v));
        EXPECT_EQ_INT(v, round + 100);
    }
    EXPECT_TRUE(ringbuf_is_empty(self->rb));
}

TEST_F(rb3, overwrite_evicts_oldest)
{
    for (int i = 1; i <= 5; i++)
        ringbuf_push_overwrite(self->rb, i);

    int got[3];
    for (int i = 0; i < 3; i++)
        ASSERT_TRUE(ringbuf_pop(self->rb, &got[i]));
    const int want[3] = {3, 4, 5};
    EXPECT_MEMEQ(got, want, sizeof want);
}
