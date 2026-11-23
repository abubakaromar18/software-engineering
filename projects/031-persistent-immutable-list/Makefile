.PHONY: build test match demo bench repl clean

build:
	cabal build all

test:
	cabal test --test-show-details=direct

# Run only part of the suite, e.g. `make match M=sharing`.
match:
	cabal test --test-show-details=direct --test-options='--match "$(M)"'

demo:
	cabal run -v0 persistent-demo

bench:
	cabal bench -v0

repl:
	cabal repl lib:persistent-structures

clean:
	rm -rf dist-newstyle
