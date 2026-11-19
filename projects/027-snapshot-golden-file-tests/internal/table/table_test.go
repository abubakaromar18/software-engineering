package table

import (
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/027-snapshot-golden-file-tests/internal/golden"
)

// TestRenderGolden renders every input in testdata/input in every format and
// compares against testdata/<input>/<format>.golden. Adding a new case is just
// dropping a CSV into testdata/input and running `go test -update`.
func TestRenderGolden(t *testing.T) {
	inputs, err := filepath.Glob(filepath.Join("testdata", "input", "*.csv"))
	if err != nil {
		t.Fatal(err)
	}
	if len(inputs) == 0 {
		t.Fatal("no inputs found in testdata/input")
	}

	for _, in := range inputs {
		name := strings.TrimSuffix(filepath.Base(in), ".csv")
		tbl := mustParseFile(t, in)

		for _, f := range Formats {
			t.Run(name+"/"+string(f), func(t *testing.T) {
				got, err := Render(tbl, Options{Format: f})
				if err != nil {
					t.Fatalf("Render: %v", err)
				}
				golden.Assert(t, name+"/"+string(f), []byte(got))
			})
		}
	}
}

// TestRenderMaxWidthGolden snapshots truncation separately, so a change to
// the ellipsis logic shows up in exactly these files.
func TestRenderMaxWidthGolden(t *testing.T) {
	tbl := mustParseFile(t, filepath.Join("testdata", "input", "long_cells.csv"))
	for _, w := range []int{12, 30} {
		name := "long_cells/box_maxwidth_" + strconv.Itoa(w)
		t.Run(name, func(t *testing.T) {
			got, err := Render(tbl, Options{Format: FormatBox, MaxWidth: w})
			if err != nil {
				t.Fatal(err)
			}
			golden.Assert(t, name, []byte(got))
		})
	}
}

// Golden files capture whole outputs; small unit tests still pin down the
// rules that produce them, so a failure points at the cause, not the symptom.

func TestInferAligns(t *testing.T) {
	tbl, err := Parse(strings.NewReader("a,b,c,d\n1,x,,NaN\n2.5,y,,Inf\n\"1,000\",z,,3\n"), ',')
	if err != nil {
		t.Fatal(err)
	}
	want := []Align{AlignRight, AlignLeft, AlignLeft, AlignLeft}
	for i := range want {
		if tbl.Aligns[i] != want[i] {
			t.Errorf("column %q: align = %v, want %v", tbl.Header[i], tbl.Aligns[i], want[i])
		}
	}
}

func TestTruncate(t *testing.T) {
	cases := []struct {
		in   string
		max  int
		want string
	}{
		{"hello", 0, "hello"},
		{"hello", 5, "hello"},
		{"hello", 4, "hel…"},
		{"Zürich", 3, "Zü…"},
		{"ab", 2, "ab"},
	}
	for _, c := range cases {
		if got := truncate(c.in, c.max); got != c.want {
			t.Errorf("truncate(%q, %d) = %q, want %q", c.in, c.max, got, c.want)
		}
	}
}

func TestParseErrors(t *testing.T) {
	if _, err := Parse(strings.NewReader(""), ','); !errors.Is(err, ErrEmpty) {
		t.Errorf("empty input: err = %v, want ErrEmpty", err)
	}
	if _, err := Parse(strings.NewReader("a,b\n1,2,3\n"), ','); err == nil {
		t.Error("ragged rows: expected an error")
	}
}

// Regression test: TrimLeadingSpace once swallowed empty tab-separated fields.
// The bug was spotted while reviewing a freshly generated golden file.
func TestParseKeepsEmptyTabFields(t *testing.T) {
	tbl, err := Parse(strings.NewReader("a\tb\tc\nx\t\tz\n"), '\t')
	if err != nil {
		t.Fatal(err)
	}
	if got := tbl.Rows[0]; len(got) != 3 || got[1] != "" || got[2] != "z" {
		t.Errorf("row = %q, want [x  z]", got)
	}
}

func TestParseTrimsSpaceAfterComma(t *testing.T) {
	tbl, err := Parse(strings.NewReader("a, b\n1, 2\n"), ',')
	if err != nil {
		t.Fatal(err)
	}
	if tbl.Header[1] != "b" || tbl.Rows[0][1] != "2" {
		t.Errorf("header=%q row=%q, want leading spaces trimmed", tbl.Header, tbl.Rows[0])
	}
}

func TestRenderRejectsBadOptions(t *testing.T) {
	tbl := &Table{Header: []string{"a"}, Aligns: []Align{AlignLeft}}
	for _, opts := range []Options{
		{MaxWidth: -1},
		{MaxWidth: 1},
		{Format: "yaml"},
	} {
		if _, err := Render(tbl, opts); err == nil {
			t.Errorf("Render(%+v): expected an error", opts)
		}
	}
}

func TestParseFormat(t *testing.T) {
	if f, err := ParseFormat("box"); err != nil || f != FormatBox {
		t.Errorf("ParseFormat(box) = %q, %v", f, err)
	}
	if _, err := ParseFormat("html"); err == nil || !strings.Contains(err.Error(), "plain, markdown, box") {
		t.Errorf("ParseFormat(html) error = %v, want list of formats", err)
	}
}

func mustParseFile(t *testing.T, path string) *Table {
	t.Helper()
	f, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	tbl, err := Parse(f, ',')
	if err != nil {
		t.Fatalf("Parse(%s): %v", path, err)
	}
	return tbl
}
