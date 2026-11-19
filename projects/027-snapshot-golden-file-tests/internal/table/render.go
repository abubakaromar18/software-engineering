package table

import (
	"fmt"
	"strings"
	"unicode/utf8"
)

// Format selects an output layout.
type Format string

const (
	FormatPlain    Format = "plain"
	FormatMarkdown Format = "markdown"
	FormatBox      Format = "box"
)

// Formats lists every supported format, in a stable order (used by the CLI
// help text and by the golden tests, which render each input in each format).
var Formats = []Format{FormatPlain, FormatMarkdown, FormatBox}

// ParseFormat validates a user-supplied format name.
func ParseFormat(s string) (Format, error) {
	for _, f := range Formats {
		if string(f) == s {
			return f, nil
		}
	}
	return "", fmt.Errorf("unknown format %q (want one of %s)", s, joinFormats())
}

func joinFormats() string {
	names := make([]string, len(Formats))
	for i, f := range Formats {
		names[i] = string(f)
	}
	return strings.Join(names, ", ")
}

// Options control rendering.
type Options struct {
	Format Format
	// MaxWidth truncates cells longer than this many characters, ending them
	// with an ellipsis. Zero means no limit.
	MaxWidth int
}

const ellipsis = "…"

// Render lays out t according to opts. The output always ends in a newline.
func Render(t *Table, opts Options) (string, error) {
	if opts.MaxWidth < 0 {
		return "", fmt.Errorf("max width must be >= 0, got %d", opts.MaxWidth)
	}
	if opts.MaxWidth == 1 {
		return "", fmt.Errorf("max width 1 leaves no room for the ellipsis; use 0 or >= 2")
	}

	// Markdown escapes "|" as "\|"; do it before measuring so columns line up.
	escape := opts.Format == FormatMarkdown
	header := prepareRow(t.Header, opts.MaxWidth, escape)
	rows := make([][]string, len(t.Rows))
	for i, r := range t.Rows {
		rows[i] = prepareRow(r, opts.MaxWidth, escape)
	}
	widths := columnWidths(header, rows)

	var b strings.Builder
	switch opts.Format {
	case FormatPlain, "":
		renderPlain(&b, header, rows, widths, t.Aligns)
	case FormatMarkdown:
		renderMarkdown(&b, header, rows, widths, t.Aligns)
	case FormatBox:
		renderBox(&b, header, rows, widths, t.Aligns)
	default:
		return "", fmt.Errorf("unknown format %q", opts.Format)
	}
	return b.String(), nil
}

// renderPlain: space-separated columns, a dashed rule under the header, and no
// trailing whitespace on any line (trailing spaces make golden diffs noisy).
func renderPlain(b *strings.Builder, header []string, rows [][]string, widths []int, aligns []Align) {
	writeLine := func(cells []string) {
		parts := make([]string, len(cells))
		for i, c := range cells {
			parts[i] = pad(c, widths[i], aligns[i])
		}
		b.WriteString(strings.TrimRight(strings.Join(parts, "  "), " "))
		b.WriteByte('\n')
	}
	writeLine(header)
	rule := make([]string, len(widths))
	for i, w := range widths {
		rule[i] = strings.Repeat("-", w)
	}
	b.WriteString(strings.Join(rule, "  "))
	b.WriteByte('\n')
	for _, r := range rows {
		writeLine(r)
	}
}

// renderMarkdown: a GitHub-flavoured Markdown table with alignment markers.
func renderMarkdown(b *strings.Builder, header []string, rows [][]string, widths []int, aligns []Align) {
	// The delimiter row needs at least three characters per column.
	for i := range widths {
		widths[i] = max(widths[i], 3)
	}
	writeLine := func(cells []string) {
		b.WriteString("|")
		for i, c := range cells {
			b.WriteString(" " + pad(c, widths[i], aligns[i]) + " |")
		}
		b.WriteByte('\n')
	}
	writeLine(header)
	b.WriteString("|")
	for i, w := range widths {
		if aligns[i] == AlignRight {
			b.WriteString(" " + strings.Repeat("-", w-1) + ": |")
		} else {
			b.WriteString(" " + strings.Repeat("-", w) + " |")
		}
	}
	b.WriteByte('\n')
	for _, r := range rows {
		writeLine(r)
	}
}

// renderBox: Unicode box-drawing borders.
func renderBox(b *strings.Builder, header []string, rows [][]string, widths []int, aligns []Align) {
	border := func(left, mid, right string) {
		b.WriteString(left)
		for i, w := range widths {
			if i > 0 {
				b.WriteString(mid)
			}
			b.WriteString(strings.Repeat("─", w+2))
		}
		b.WriteString(right + "\n")
	}
	writeLine := func(cells []string) {
		b.WriteString("│")
		for i, c := range cells {
			b.WriteString(" " + pad(c, widths[i], aligns[i]) + " │")
		}
		b.WriteByte('\n')
	}
	border("┌", "┬", "┐")
	writeLine(header)
	border("├", "┼", "┤")
	for _, r := range rows {
		writeLine(r)
	}
	border("└", "┴", "┘")
}

func columnWidths(header []string, rows [][]string) []int {
	widths := make([]int, len(header))
	for i, h := range header {
		widths[i] = width(h)
	}
	for _, r := range rows {
		for i, c := range r {
			widths[i] = max(widths[i], width(c))
		}
	}
	return widths
}

// width counts runes, so "é" and "…" are one column each. Wide CJK glyphs and
// emoji are not measured specially; see the README's trade-offs section.
func width(s string) int { return utf8.RuneCountInString(s) }

func pad(s string, w int, a Align) string {
	gap := strings.Repeat(" ", w-width(s))
	if a == AlignRight {
		return gap + s
	}
	return s + gap
}

// prepareRow truncates each cell and, for Markdown, escapes pipes.
func prepareRow(cells []string, maxWidth int, escape bool) []string {
	out := make([]string, len(cells))
	for i, c := range cells {
		out[i] = truncate(c, maxWidth)
		if escape {
			out[i] = escapePipes(out[i])
		}
	}
	return out
}

func truncate(s string, maxWidth int) string {
	if maxWidth == 0 || width(s) <= maxWidth {
		return s
	}
	runes := []rune(s)
	return string(runes[:maxWidth-1]) + ellipsis
}

func escapePipes(s string) string { return strings.ReplaceAll(s, "|", `\|`) }
