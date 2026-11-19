package golden

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// recorder is a fake TB that captures failures instead of stopping the test,
// so we can assert on how the golden helper itself fails.
type recorder struct {
	errors []string
	fatal  bool
	logs   []string
}

func (r *recorder) Helper() {}
func (r *recorder) Fatalf(format string, args ...any) {
	r.fatal = true
	r.errors = append(r.errors, fmt.Sprintf(format, args...))
}
func (r *recorder) Errorf(format string, args ...any) {
	r.errors = append(r.errors, fmt.Sprintf(format, args...))
}
func (r *recorder) Logf(format string, args ...any) {
	r.logs = append(r.logs, fmt.Sprintf(format, args...))
}

func TestAssertMatch(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "ok.golden"), "hello\n")

	var r recorder
	Asserter{Dir: dir}.Assert(&r, "ok", []byte("hello\n"))
	if len(r.errors) != 0 {
		t.Fatalf("unexpected failure: %v", r.errors)
	}
}

func TestAssertToleratesCRLFGoldenFile(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "crlf.golden"), "a\r\nb\r\n")

	var r recorder
	Asserter{Dir: dir}.Assert(&r, "crlf", []byte("a\nb\n"))
	if len(r.errors) != 0 {
		t.Fatalf("CRLF golden file should match LF output: %v", r.errors)
	}
}

func TestAssertMismatchShowsDiff(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "x.golden"), "one\ntwo\nthree\n")

	var r recorder
	Asserter{Dir: dir}.Assert(&r, "x", []byte("one\n2\nthree\n"))
	if len(r.errors) != 1 || r.fatal {
		t.Fatalf("want one non-fatal error, got fatal=%v errors=%v", r.fatal, r.errors)
	}
	msg := r.errors[0]
	for _, want := range []string{"- two", "+ 2", "  one", "-update"} {
		if !strings.Contains(msg, want) {
			t.Errorf("failure message missing %q:\n%s", want, msg)
		}
	}
}

func TestAssertMissingFileExplainsHowToCreate(t *testing.T) {
	var r recorder
	Asserter{Dir: t.TempDir()}.Assert(&r, "nope", []byte("x"))
	if !r.fatal || !strings.Contains(r.errors[0], "does not exist") || !strings.Contains(r.errors[0], "-update") {
		t.Fatalf("want fatal 'does not exist ... -update', got %v", r.errors)
	}
}

func TestUpdateWritesNestedGoldenFile(t *testing.T) {
	dir := t.TempDir()
	a := Asserter{Dir: dir, Update: true}

	var r recorder
	a.Assert(&r, "group/case", []byte("snapshot\n"))
	if len(r.errors) != 0 {
		t.Fatalf("update failed: %v", r.errors)
	}
	got, err := os.ReadFile(filepath.Join(dir, "group", "case.golden"))
	if err != nil || string(got) != "snapshot\n" {
		t.Fatalf("golden file = %q, %v", got, err)
	}

	// After an update, a normal run must pass: update and compare agree.
	var r2 recorder
	Asserter{Dir: dir}.Assert(&r2, "group/case", []byte("snapshot\n"))
	if len(r2.errors) != 0 {
		t.Fatalf("compare after update failed: %v", r2.errors)
	}
}

func TestDiff(t *testing.T) {
	cases := []struct {
		name, want, got, expect string
	}{
		{"equal", "a\nb", "a\nb", "  a\n  b\n"},
		{"changed line", "a\nb\nc", "a\nB\nc", "  a\n- b\n+ B\n  c\n"},
		{"added line", "a\nc", "a\nb\nc", "  a\n+ b\n  c\n"},
		{"removed line", "a\nb\nc", "a\nc", "  a\n- b\n  c\n"},
		{"trailing space made visible", "a", "a  ", "- a\n+ a··\n"},
		{"empty want", "", "x", "+ x\n"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if d := Diff(c.want, c.got); d != c.expect {
				t.Errorf("Diff mismatch\n got: %q\nwant: %q", d, c.expect)
			}
		})
	}
}

func writeFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}
