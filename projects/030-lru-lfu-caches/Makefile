.PHONY: build test race cover fuzz bench sim vet fmt clean

build:
	go build -o bin/cachesim ./cmd/cachesim

test:
	go test ./...

# The concurrency tests are most useful under the race detector.
race:
	go test -race -count=1 ./...

cover:
	go test -cover ./...

# Search for op sequences where LRU/LFU disagree with their naive models.
fuzz:
	go test -run='^$$' -fuzz=FuzzCachesMatchModel -fuzztime=30s .

bench:
	go test -run='^$$' -bench=. -benchmem -cpu=1,4 .

# Compare the policies on every workload.
sim:
	@for w in zipf scan-mix shift loop; do go run ./cmd/cachesim -workload $$w; echo; done

vet:
	go vet ./...

fmt:
	gofmt -l -w .

clean:
	rm -rf bin
