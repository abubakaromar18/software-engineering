.PHONY: build test race run vet

build:
	go build ./...

test:
	go test ./...

race:
	go test -race -count=1 ./...

vet:
	go vet ./...

run:
	go run ./cmd/tickerdemo
