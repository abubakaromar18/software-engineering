package dlist

import (
	"slices"
	"testing"
)

func values[T any](l *List[T]) []T {
	var out []T
	for n := l.Front(); n != nil; n = n.Next() {
		out = append(out, n.Value)
	}
	return out
}

func backwards[T any](l *List[T]) []T {
	var out []T
	for n := l.Back(); n != nil; n = n.Prev() {
		out = append(out, n.Value)
	}
	return out
}

func TestZeroValueIsEmpty(t *testing.T) {
	var l List[int]
	if l.Len() != 0 || l.Front() != nil || l.Back() != nil {
		t.Fatalf("zero list not empty: len=%d", l.Len())
	}
}

func TestPushMoveRemove(t *testing.T) {
	var l List[int]
	a := l.PushFront(1)
	l.PushFront(2)
	c := l.PushFront(3) // 3 2 1

	if got := values(&l); !slices.Equal(got, []int{3, 2, 1}) {
		t.Fatalf("after pushes: %v", got)
	}
	l.MoveToFront(a) // 1 3 2
	l.MoveToFront(a) // no-op when already at front
	if got := values(&l); !slices.Equal(got, []int{1, 3, 2}) {
		t.Fatalf("after move: %v", got)
	}
	l.Remove(c) // 1 2
	if got, back := values(&l), backwards(&l); !slices.Equal(got, []int{1, 2}) || !slices.Equal(back, []int{2, 1}) {
		t.Fatalf("after remove: fwd=%v back=%v", got, back)
	}
	if c.Next() != nil || c.Prev() != nil {
		t.Fatal("detached node should have no neighbours")
	}
	l.InsertAfter(9, a) // 1 9 2
	if got := values(&l); !slices.Equal(got, []int{1, 9, 2}) || l.Len() != 3 {
		t.Fatalf("after insert: %v len=%d", got, l.Len())
	}
}

func TestNodeCanMoveBetweenLists(t *testing.T) {
	var src, dst List[string]
	n := src.PushFront("x")
	src.Remove(n)
	dst.PushNodeFront(n)
	if src.Len() != 0 || dst.Len() != 1 || dst.Front() != n {
		t.Fatalf("relink failed: src=%d dst=%d", src.Len(), dst.Len())
	}
}

func TestMisuse(t *testing.T) {
	cases := map[string]func(){
		"remove foreign node": func() {
			var a, b List[int]
			b.Remove(a.PushFront(1))
		},
		"push linked node": func() {
			var a, b List[int]
			b.PushNodeFront(a.PushFront(1))
		},
		"move foreign node": func() {
			var a, b List[int]
			b.MoveToFront(a.PushFront(1))
		},
		"insert after foreign mark": func() {
			var a, b List[int]
			b.InsertAfter(2, a.PushFront(1))
		},
	}
	for name, fn := range cases {
		t.Run(name, func(t *testing.T) {
			defer func() {
				if recover() == nil {
					t.Fatal("expected panic")
				}
			}()
			fn()
		})
	}
}
