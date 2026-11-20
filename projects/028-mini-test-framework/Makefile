# mtest — build the library, the self-tests and the example suite.
#
#   make            build everything into build/
#   make test       run self-tests, example suite and end-to-end CLI checks
#   make sanitize   the same under AddressSanitizer + UBSan
#   make valgrind   run the in-process self-tests under valgrind
#   make clean

CC      ?= cc
CFLAGS  ?= -O2 -g
WARN    := -std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wstrict-prototypes \
           -Wmissing-prototypes -Werror
BUILD   ?= build

LIB_SRC := src/util.c src/filter.c src/options.c src/registry.c src/assert.c \
           src/runner.c src/report_console.c src/report_junit.c src/main.c
LIB_OBJ := $(LIB_SRC:src/%.c=$(BUILD)/lib/%.o)
LIB     := $(BUILD)/libmtest.a
MAIN    := $(BUILD)/lib/mtest_main.o

SELF_SRC    := $(wildcard tests/test_*.c)
EXAMPLE_SRC := examples/ringbuf.c examples/test_ringbuf.c

SELF    := $(BUILD)/self_tests
EXAMPLE := $(BUILD)/example_tests
SAMPLE  := $(BUILD)/sample_outcomes

.PHONY: all test sanitize valgrind clean
all: $(SELF) $(EXAMPLE) $(SAMPLE)

$(BUILD)/lib/%.o: src/%.c include/mtest.h src/internal.h
	@mkdir -p $(@D)
	$(CC) $(WARN) $(CFLAGS) -Iinclude -c $< -o $@

$(LIB): $(LIB_OBJ)
	$(AR) rcs $@ $^

# Test files are compiled without -Wmissing-prototypes: TEST() bodies are
# static functions, but helper probes in the self-tests need not be.
TEST_WARN := $(filter-out -Wmissing-prototypes,$(WARN))

$(SELF): $(SELF_SRC) $(LIB) $(MAIN)
	$(CC) $(TEST_WARN) $(CFLAGS) -Iinclude -Isrc $(SELF_SRC) $(MAIN) $(LIB) -o $@

$(EXAMPLE): $(EXAMPLE_SRC) examples/ringbuf.h $(LIB) $(MAIN)
	$(CC) $(TEST_WARN) $(CFLAGS) -Iinclude $(EXAMPLE_SRC) $(MAIN) $(LIB) -o $@

$(SAMPLE): tests/sample/sample_outcomes.c $(LIB) $(MAIN)
	$(CC) $(TEST_WARN) $(CFLAGS) -Iinclude $< $(MAIN) $(LIB) -o $@

test: all
	./$(SELF) --timeout=10
	./$(EXAMPLE)
	tests/selftest.sh ./$(SAMPLE)

# Sanitizers would intercept the deliberate SIGSEGV in the crash tests;
# handle_segv=0 lets it reach the runner as a real signal.
sanitize:
	ASAN_OPTIONS=handle_segv=0:detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
	    $(MAKE) BUILD=build/san \
	    CFLAGS="-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer" test

valgrind: all
	valgrind --error-exitcode=99 --leak-check=full --errors-for-leak-kinds=definite \
	    --trace-children=no ./$(SELF) --no-fork --filter='-fork.*'

clean:
	rm -rf build
