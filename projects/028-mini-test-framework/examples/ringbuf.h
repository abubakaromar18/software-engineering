/* A fixed-capacity FIFO of ints: the "code under test" for the example
 * suite that shows how a project would use mtest. */
#ifndef RINGBUF_H
#define RINGBUF_H

#include <stdbool.h>
#include <stddef.h>

typedef struct ringbuf ringbuf;

/* Returns NULL if capacity is 0 or allocation fails. */
ringbuf *ringbuf_new(size_t capacity);
void ringbuf_free(ringbuf *rb);

/* Returns false (and leaves the buffer unchanged) when full. */
bool ringbuf_push(ringbuf *rb, int value);
/* Returns false when empty; otherwise stores the oldest value in *out. */
bool ringbuf_pop(ringbuf *rb, int *out);
/* Like push, but when full evicts the oldest value first. */
void ringbuf_push_overwrite(ringbuf *rb, int value);

size_t ringbuf_len(const ringbuf *rb);
size_t ringbuf_capacity(const ringbuf *rb);
bool ringbuf_is_empty(const ringbuf *rb);
bool ringbuf_is_full(const ringbuf *rb);

#endif /* RINGBUF_H */
