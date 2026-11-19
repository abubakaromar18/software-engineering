// Package table parses delimited text into a Table and renders it in several
// human-readable layouts. Rendering is pure (Table in, string out), which is
// what makes it a good fit for golden-file testing.
package table

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"
	"unicode"
)

// Align is the horizontal alignment of a column.
type Align int

const (
	AlignLeft Align = iota
	AlignRight
)

// Table is a header row plus data rows. Every row has len(Header) cells.
type Table struct {
	Header []string
	Rows   [][]string
	Aligns []Align // one per column, inferred by Parse
}

// ErrEmpty is returned when the input has no header row.
var ErrEmpty = errors.New("input is empty: expected a header row")

// Parse reads delimited records from r. The first record is the header.
// Columns whose every non-empty data cell is numeric are right-aligned.
func Parse(r io.Reader, delim rune) (*Table, error) {
	cr := csv.NewReader(r)
	cr.Comma = delim
	// Trimming leading space makes "a, b" read as "b", but with a whitespace
	// delimiter it would swallow empty fields ("x\t\ty" would lose a column).
	cr.TrimLeadingSpace = !unicode.IsSpace(delim)

	records, err := cr.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("parse input: %w", err)
	}
	if len(records) == 0 {
		return nil, ErrEmpty
	}

	t := &Table{Header: records[0], Rows: records[1:]}
	t.Aligns = inferAligns(t)
	return t, nil
}

// inferAligns right-aligns columns that contain only numbers (ignoring blanks).
// A column with no data at all stays left-aligned.
func inferAligns(t *Table) []Align {
	aligns := make([]Align, len(t.Header))
	for col := range t.Header {
		numeric, seen := true, false
		for _, row := range t.Rows {
			cell := strings.TrimSpace(row[col])
			if cell == "" {
				continue
			}
			seen = true
			if !isNumber(cell) {
				numeric = false
				break
			}
		}
		if numeric && seen {
			aligns[col] = AlignRight
		}
	}
	return aligns
}

func isNumber(s string) bool {
	s = strings.ReplaceAll(s, ",", "") // allow thousands separators: 1,234.5
	// ParseFloat accepts "NaN" and "Inf"; a cell like that is a word, not a number.
	if !strings.ContainsAny(s, "0123456789") {
		return false
	}
	_, err := strconv.ParseFloat(s, 64)
	return err == nil
}
