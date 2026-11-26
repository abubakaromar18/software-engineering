# Thin convenience wrapper around CMake.
BUILD_DIR ?= build
BUILD_TYPE ?= Release
CMAKE_FLAGS ?=
JOBS ?= $(shell nproc 2>/dev/null || echo 4)

.PHONY: all build test run sanitize clean

all: build

build:
	cmake -S . -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=$(BUILD_TYPE) $(CMAKE_FLAGS)
	cmake --build $(BUILD_DIR) -j $(JOBS)

test: build
	ctest --test-dir $(BUILD_DIR) --output-on-failure -j $(JOBS)

run: build
	./$(BUILD_DIR)/heap_scheduler $(ARGS)

# Debug build of the test suite under AddressSanitizer + UBSan.
sanitize:
	$(MAKE) test BUILD_DIR=build-asan BUILD_TYPE=Debug CMAKE_FLAGS=-DHEAPQ_SANITIZE=ON

clean:
	rm -rf build build-asan
