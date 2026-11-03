# Thin convenience wrapper around CMake.
BUILD_DIR ?= build
CONFIG    ?= Debug

.PHONY: all build test run clean

all: build

build:
	cmake -S . -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=$(CONFIG)
	cmake --build $(BUILD_DIR) -j

test: build
	ctest --test-dir $(BUILD_DIR) --output-on-failure

run: build
	./$(BUILD_DIR)/vfs-tree examples/project.manifest

clean:
	rm -rf $(BUILD_DIR)
