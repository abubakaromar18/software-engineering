.PHONY: build test update vet fmt clean

build:
	go build -o bin/tabfmt ./cmd/tabfmt

test:
	go test ./...

# Regenerate every golden file from current output. Review the diff before committing!
update:
	go test ./... -update

vet:
	go vet ./...

fmt:
	gofmt -l -w .

clean:
	rm -rf bin
