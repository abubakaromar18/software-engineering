// Command tabfmt formats CSV (or other delimited text) as an aligned table.
//
//	tabfmt [-format plain|markdown|box] [-delim ,] [-max-width N] [FILE]
//
// With no FILE, or FILE "-", it reads standard input.
package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"unicode/utf8"

	"github.com/abubakaromar18/software-engineering/projects/027-snapshot-golden-file-tests/internal/table"
)

// Exit codes.
const (
	exitOK    = 0
	exitError = 1 // bad input or I/O failure
	exitUsage = 2 // bad flags or arguments
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}

// run is the whole program with its dependencies passed in, so tests can
// drive it in-process and snapshot stdout, stderr and the exit code.
func run(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("tabfmt", flag.ContinueOnError)
	fs.SetOutput(stderr)
	format := fs.String("format", string(table.FormatPlain), "output format: plain, markdown or box")
	delim := fs.String("delim", ",", `field delimiter: a single character, or "\t" for tab`)
	maxWidth := fs.Int("max-width", 0, "truncate cells longer than N characters (0 = no limit)")
	fs.Usage = func() {
		fmt.Fprintln(stderr, "usage: tabfmt [flags] [FILE]")
		fs.PrintDefaults()
	}

	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return exitOK
		}
		return exitUsage
	}

	f, err := table.ParseFormat(*format)
	if err != nil {
		return usageError(stderr, err)
	}
	d, err := parseDelim(*delim)
	if err != nil {
		return usageError(stderr, err)
	}
	if fs.NArg() > 1 {
		return usageError(stderr, fmt.Errorf("expected at most one FILE, got %d", fs.NArg()))
	}

	in, closeIn, err := openInput(fs.Arg(0), stdin)
	if err != nil {
		fmt.Fprintf(stderr, "tabfmt: %v\n", err)
		return exitError
	}
	defer closeIn()

	t, err := table.Parse(in, d)
	if err != nil {
		fmt.Fprintf(stderr, "tabfmt: %v\n", err)
		return exitError
	}
	out, err := table.Render(t, table.Options{Format: f, MaxWidth: *maxWidth})
	if err != nil {
		return usageError(stderr, err)
	}
	if _, err := io.WriteString(stdout, out); err != nil {
		fmt.Fprintf(stderr, "tabfmt: write output: %v\n", err)
		return exitError
	}
	return exitOK
}

func usageError(stderr io.Writer, err error) int {
	fmt.Fprintf(stderr, "tabfmt: %v\n", err)
	return exitUsage
}

func parseDelim(s string) (rune, error) {
	if s == `\t` {
		return '\t', nil
	}
	r, size := utf8.DecodeRuneInString(s)
	if size == 0 || size != len(s) || r == '\n' || r == '\r' || r == '"' {
		return 0, fmt.Errorf("invalid delimiter %q: want one character other than quote or newline", s)
	}
	return r, nil
}

// openInput returns stdin for "" or "-", otherwise the named file.
func openInput(path string, stdin io.Reader) (io.Reader, func(), error) {
	if path == "" || path == "-" {
		return stdin, func() {}, nil
	}
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	return f, func() { f.Close() }, nil
}
