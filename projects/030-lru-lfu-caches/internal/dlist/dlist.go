// Package dlist is a small generic doubly linked list with a sentinel root.
//
// It differs from container/list in two ways that matter for caches:
//
//   - It is generic, so values are stored inline without interface boxing.
//   - Nodes can be unlinked from one list and relinked into another
//     (PushNodeFront) without allocating, which the LFU cache relies on when
//     it promotes an entry to the next frequency bucket.
//
// A List must not be copied after first use: the sentinel points to itself.
package dlist

// Node is an element of a List. Value is freely readable and writable.
type Node[T any] struct {
	Value T

	prev, next *Node[T]
	list       *List[T]
}

// Next returns the following node, or nil at the end of the list.
func (n *Node[T]) Next() *Node[T] {
	if n.list == nil || n.next == &n.list.root {
		return nil
	}
	return n.next
}

// Prev returns the preceding node, or nil at the front of the list.
func (n *Node[T]) Prev() *Node[T] {
	if n.list == nil || n.prev == &n.list.root {
		return nil
	}
	return n.prev
}

// List is a doubly linked list. The zero value is an empty list ready to use.
type List[T any] struct {
	root Node[T] // sentinel: root.next is the front, root.prev is the back
	len  int
}

func (l *List[T]) lazyInit() {
	if l.root.next == nil {
		l.root.next = &l.root
		l.root.prev = &l.root
	}
}

// Len returns the number of nodes in the list. O(1).
func (l *List[T]) Len() int { return l.len }

// Front returns the first node, or nil if the list is empty.
func (l *List[T]) Front() *Node[T] {
	if l.len == 0 {
		return nil
	}
	return l.root.next
}

// Back returns the last node, or nil if the list is empty.
func (l *List[T]) Back() *Node[T] {
	if l.len == 0 {
		return nil
	}
	return l.root.prev
}

// insert links n after at and returns n.
func (l *List[T]) insert(n, at *Node[T]) *Node[T] {
	n.prev = at
	n.next = at.next
	at.next.prev = n
	at.next = n
	n.list = l
	l.len++
	return n
}

// PushFront allocates a node holding v at the front of the list.
func (l *List[T]) PushFront(v T) *Node[T] {
	l.lazyInit()
	return l.insert(&Node[T]{Value: v}, &l.root)
}

// PushNodeFront links an existing, detached node at the front of the list.
// It panics if n still belongs to a list, since that would corrupt both.
func (l *List[T]) PushNodeFront(n *Node[T]) {
	if n.list != nil {
		panic("dlist: PushNodeFront of a node that is still linked")
	}
	l.lazyInit()
	l.insert(n, &l.root)
}

// InsertAfter allocates a node holding v immediately after mark.
// It panics if mark does not belong to l.
func (l *List[T]) InsertAfter(v T, mark *Node[T]) *Node[T] {
	if mark.list != l {
		panic("dlist: InsertAfter with a mark from another list")
	}
	return l.insert(&Node[T]{Value: v}, mark)
}

// MoveToFront moves n to the front of l. It panics if n does not belong to l.
func (l *List[T]) MoveToFront(n *Node[T]) {
	if n.list != l {
		panic("dlist: MoveToFront of a node from another list")
	}
	if l.root.next == n {
		return
	}
	l.unlink(n)
	l.insert(n, &l.root)
}

// Remove unlinks n from l, leaving it detached and reusable.
// It panics if n does not belong to l.
func (l *List[T]) Remove(n *Node[T]) {
	if n.list != l {
		panic("dlist: Remove of a node from another list")
	}
	l.unlink(n)
}

func (l *List[T]) unlink(n *Node[T]) {
	n.prev.next = n.next
	n.next.prev = n.prev
	n.prev, n.next, n.list = nil, nil, nil // avoid retaining neighbours; mark detached
	l.len--
}
