// Package golden implements snapshot ("golden file") assertions for tests.
//
// A golden file stores the expected output of a test. Assert compares the
// actual output against it and fails with a line diff on mismatch. Running
//
//	go test ./... -update
//
// rewrites every golden file with the current output instead of comparing, so
// an intentional change in output is a one-command, reviewable diff.
package golden

import (
	"bytes"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// update is registered on the test binary's flag set when this package is
// imported, so every package whose tests use golden accepts -update.
var update = flag.Bool("update", false, "rewrite golden files with the current output")

// TB is the subset of testing.TB that Assert needs. Accepting an interface
// lets golden's own tests pass a recorder and inspect failures.
type TB interface {
	Helper()
	Fatalf(format string, args ...any)
	Errorf(format string, args ...any)
	Logf(format string, args ...any)
}

// Asserter compares output against golden files under Dir.
type Asserter struct {
	Dir    string // directory holding *.golden files, usually "testdata"
	Update bool   // write instead of compare
}

// Default returns an Asserter rooted at ./testdata that honours -update.
func Default() Asserter {
	return Asserter{Dir: "testdata", Update: *update}
}

// Assert is shorthand for Default().Assert.
func Assert(t TB, name string, got []byte) {
	t.Helper()
	Default().Assert(t, name, got)
}

// Path returns the golden file path for a test name. Names may contain "/"
// (as produced by t.Name() for subtests) to group files into directories.
func (a Asserter) Path(name string) string {
	return filepath.Join(a.Dir, filepath.FromSlash(name)+".golden")
}

// Assert checks got against the golden file for name.
func (a Asserter) Assert(t TB, name string, got []byte) {
	t.Helper()
	path := a.Path(name)

	if a.Update {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatalf("golden: create dir for %s: %v", path, err)
			return
		}
		if err := os.WriteFile(path, got, 0o644); err != nil {
			t.Fatalf("golden: write %s: %v", path, err)
			return
		}
		t.Logf("golden: updated %s", path)
		return
	}

	want, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		t.Fatalf("golden: %s does not exist; run `go test -update` to create it", path)
		return
	}
	if err != nil {
		t.Fatalf("golden: read %s: %v", path, err)
		return
	}

	// Normalise line endings so a checkout with core.autocrlf=true still passes.
	want = bytes.ReplaceAll(want, []byte("\r\n"), []byte("\n"))
	if !bytes.Equal(got, want) {
		t.Errorf("golden: output does not match %s (run `go test -update` if the change is intended)\n%s",
			path, Diff(string(want), string(got)))
	}
}

// Diff returns a minimal line diff from want to got, using "-" for lines only
// in want and "+" for lines only in got. It is based on the longest common
// subsequence, which is plenty for test-sized outputs (O(n·m) memory).
func Diff(want, got string) string {
	a := splitLines(want)
	b := splitLines(got)

	// lcs[i][j] = length of the LCS of a[i:] and b[j:].
	lcs := make([][]int, len(a)+1)
	for i := range lcs {
		lcs[i] = make([]int, len(b)+1)
	}
	for i := len(a) - 1; i >= 0; i-- {
		for j := len(b) - 1; j >= 0; j-- {
			if a[i] == b[j] {
				lcs[i][j] = lcs[i+1][j+1] + 1
			} else {
				lcs[i][j] = max(lcs[i+1][j], lcs[i][j+1])
			}
		}
	}

	var out strings.Builder
	i, j := 0, 0
	for i < len(a) || j < len(b) {
		switch {
		case i < len(a) && j < len(b) && a[i] == b[j]:
			fmt.Fprintf(&out, "  %s\n", visible(a[i]))
			i++
			j++
		// On a tie, emit the removal first so changes read "- old / + new".
		case i < len(a) && (j == len(b) || lcs[i+1][j] >= lcs[i][j+1]):
			fmt.Fprintf(&out, "- %s\n", visible(a[i]))
			i++
		default:
			fmt.Fprintf(&out, "+ %s\n", visible(b[j]))
			j++
		}
	}
	return out.String()
}

func splitLines(s string) []string {
	if s == "" {
		return nil
	}
	return strings.Split(s, "\n")
}

// visible marks trailing whitespace, the most common invisible golden diff.
func visible(line string) string {
	trimmed := strings.TrimRight(line, " \t")
	if trimmed == line {
		return line
	}
	return trimmed + strings.Repeat("·", len(line)-len(trimmed))
}
