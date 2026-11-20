#include "ringbuf.h"

#include <stdint.h>
#include <stdlib.h>

struct ringbuf {
    size_t capacity;
    size_t head;   /* index of the oldest element */
    size_t len;
    int items[];   /* flexible array member: one allocation */
};

ringbuf *ringbuf_new(size_t capacity)
{
    if (capacity == 0 || capacity > (SIZE_MAX - sizeof(ringbuf)) / sizeof(int))
        return NULL;
    ringbuf *rb = malloc(sizeof *rb + capacity * sizeof(int));
    if (!rb)
        return NULL;
    rb->capacity = capacity;
    rb->head = 0;
    rb->len = 0;
    return rb;
}

void ringbuf_free(ringbuf *rb) { free(rb); }

bool ringbuf_push(ringbuf *rb, int value)
{
    if (rb->len == rb->capacity)
        return false;
    rb->items[(rb->head + rb->len) % rb->capacity] = value;
    rb->len++;
    return true;
}

bool ringbuf_pop(ringbuf *rb, int *out)
{
    if (rb->len == 0)
        return false;
    *out = rb->items[rb->head];
    rb->head = (rb->head + 1) % rb->capacity;
    rb->len--;
    return true;
}

void ringbuf_push_overwrite(ringbuf *rb, int value)
{
    if (rb->len == rb->capacity) {
        int dropped;
        ringbuf_pop(rb, &dropped);
    }
    ringbuf_push(rb, value);
}

size_t ringbuf_len(const ringbuf *rb) { return rb->len; }
size_t ringbuf_capacity(const ringbuf *rb) { return rb->capacity; }
bool ringbuf_is_empty(const ringbuf *rb) { return rb->len == 0; }
bool ringbuf_is_full(const ringbuf *rb) { return rb->len == rb->capacity; }
