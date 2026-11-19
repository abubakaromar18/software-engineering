package main

import (
	"bytes"
	"fmt"
	"strings"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/027-snapshot-golden-file-tests/internal/golden"
)

const sampleCSV = "service,p99_ms,status\napi,42,ok\nbilling,1300,degraded\nsearch,87.5,ok\n"

// TestCLIGolden runs the program in-process and snapshots everything a user
// would observe: exit code, stdout and stderr. Error messages and --help text
// are part of the CLI's contract too, so they get golden files as well.
func TestCLIGolden(t *testing.T) {
	cases := []struct {
		name  string
		args  []string
		stdin string
	}{
		{"default_plain", nil, sampleCSV},
		{"markdown", []string{"-format", "markdown"}, sampleCSV},
		{"box_from_file", []string{"-format", "box", "-delim", `\t`, "testdata/services.tsv"}, ""},
		{"stdin_dash_semicolon", []string{"-delim", ";", "-"}, "k;v\nalpha;1\nbeta;22\n"},
		{"max_width", []string{"-max-width", "5"}, sampleCSV},
		{"help", []string{"-h"}, ""},
		{"err_unknown_format", []string{"-format", "yaml"}, sampleCSV},
		{"err_bad_delim", []string{"-delim", "::"}, sampleCSV},
		{"err_too_many_args", []string{"a.csv", "b.csv"}, ""},
		{"err_missing_file", []string{"testdata/missing.csv"}, ""},
		{"err_ragged_rows", nil, "a,b\n1,2,3\n"},
		{"err_empty_input", nil, ""},
		{"err_max_width_one", []string{"-max-width", "1"}, sampleCSV},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := run(c.args, strings.NewReader(c.stdin), &stdout, &stderr)
			golden.Assert(t, c.name, transcript(c.args, code, stdout.String(), stderr.String()))
		})
	}
}

// transcript serialises one run into a single reviewable text snapshot.
func transcript(args []string, code int, stdout, stderr string) []byte {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", strings.TrimSpace("$ tabfmt "+strings.Join(args, " ")))
	fmt.Fprintf(&b, "exit: %d\n", code)
	fmt.Fprintf(&b, "--- stdout ---\n%s", stdout)
	fmt.Fprintf(&b, "--- stderr ---\n%s", stderr)
	return []byte(b.String())
}

func TestParseDelim(t *testing.T) {
	ok := map[string]rune{",": ',', ";": ';', `\t`: '\t', "|": '|', "·": '·'}
	for in, want := range ok {
		if got, err := parseDelim(in); err != nil || got != want {
			t.Errorf("parseDelim(%q) = %q, %v; want %q", in, got, err, want)
		}
	}
	for _, in := range []string{"", "ab", "\n", `"`} {
		if _, err := parseDelim(in); err == nil {
			t.Errorf("parseDelim(%q): expected an error", in)
		}
	}
}
