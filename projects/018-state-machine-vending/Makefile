.PHONY: build test lint verify demo all

all: lint test verify

build:
	cargo build --release

test:
	cargo test

lint:
	cargo fmt --check
	cargo clippy --all-targets -- -D warnings

# Confirms each compile_fail doctest fails for the reason it documents.
verify:
	python3 scripts/verify_compile_fail.py

demo:
	cargo run -q -- --demo < examples/demo.txt
