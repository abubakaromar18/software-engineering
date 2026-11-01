.PHONY: all build test race vet fmt demo clean

all: fmt vet test

build:
	go build -o bin/paydemo ./cmd/paydemo

test:
	go test ./...

race:
	go test -race -count=1 ./...

vet:
	go vet ./...

fmt:
	@test -z "$$(gofmt -l .)" || (gofmt -l . && echo "run gofmt -w ." && exit 1)

demo:
	go run ./cmd/paydemo -providers swiftpay,ledgerly,quickcoin -source tok_outage -refund

clean:
	rm -rf bin
