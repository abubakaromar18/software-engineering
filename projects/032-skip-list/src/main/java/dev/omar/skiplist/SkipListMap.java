package dev.omar.skiplist;

import java.util.AbstractMap;
import java.util.AbstractSet;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.IdentityHashMap;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.Set;
import java.util.Spliterator;
import java.util.Spliterators;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

/**
 * A sorted map backed by an <em>indexable</em> skip list (Pugh, 1990; spans as in Redis zsets).
 *
 * <p>Every node owns a tower of forward pointers. Level 0 is an ordinary sorted linked list;
 * each higher level skips over a random subset of the level below, so a search descends from
 * the top level and moves right while the next key is smaller, giving expected
 * {@code O(log n)} cost for {@link #get}, {@link #put}, {@link #remove} and the navigation
 * methods.
 *
 * <p>Each forward pointer also stores a <em>span</em>: how many level-0 steps it jumps.
 * Summing spans along a search path yields a key's position, which makes {@link #rank},
 * {@link #select} and {@link RangeView#size()} {@code O(log n)} as well — something
 * {@link java.util.TreeMap} cannot do without walking the range.
 *
 * <p>Keys must be non-null and mutually comparable, either naturally or through the supplied
 * {@link Comparator}. Values may be null. This class is <strong>not thread-safe</strong>; its
 * iterators are fail-fast (best effort) like those in {@code java.util}. For a concurrent skip
 * list see {@link java.util.concurrent.ConcurrentSkipListMap}.
 *
 * @param <K> key type
 * @param <V> value type
 */
public final class SkipListMap<K, V> extends AbstractMap<K, V> {

    /** Enough for 2^32 entries with p = 1/2; levels beyond log_{1/p}(n) carry no benefit. */
    public static final int MAX_LEVEL = 32;

    private final Comparator<? super K> comparator;
    private final LevelGenerator levelGenerator;
    private final Node<K, V> head = new Node<>(null, null, MAX_LEVEL);

    /** Number of levels currently in use; the head's pointers above this are ignored. */
    private int level = 1;
    private int size;
    /** Bumped on every structural change so iterators can detect concurrent modification. */
    private int modCount;

    private Set<Map.Entry<K, V>> entrySet;

    /** A map ordered by the keys' natural ordering. */
    public SkipListMap() {
        this(null, new GeometricLevelGenerator());
    }

    /** A map ordered by {@code comparator} ({@code null} means natural ordering). */
    public SkipListMap(Comparator<? super K> comparator) {
        this(comparator, new GeometricLevelGenerator());
    }

    /**
     * @param comparator     key ordering, or {@code null} for natural ordering
     * @param levelGenerator source of node heights; inject a seeded or scripted one for tests
     */
    public SkipListMap(Comparator<? super K> comparator, LevelGenerator levelGenerator) {
        this.comparator = comparator;
        this.levelGenerator = Objects.requireNonNull(levelGenerator, "levelGenerator");
    }

    // ---------------------------------------------------------------------------------------
    // Core map operations
    // ---------------------------------------------------------------------------------------

    @Override
    public int size() {
        return size;
    }

    @Override
    public boolean containsKey(Object key) {
        return findNode(key) != null;
    }

    @Override
    public V get(Object key) {
        Node<K, V> node = findNode(key);
        return node == null ? null : node.value;
    }

    /**
     * Associates {@code value} with {@code key}, replacing any previous value.
     *
     * <p>The search records, for every level, the last node before the insertion point
     * ({@code update[i]}) and its 0-based position ({@code rank[i]} = number of entries strictly
     * before {@code update[i]}'s successor). Those positions let us split the predecessor's
     * span exactly when the new node is linked in.
     */
    @Override
    public V put(K key, V value) {
        Objects.requireNonNull(key, "key");
        Node<K, V>[] update = newNodeArray(MAX_LEVEL);
        int[] rank = new int[MAX_LEVEL];

        Node<K, V> x = head;
        for (int i = level - 1; i >= 0; i--) {
            rank[i] = (i == level - 1) ? 0 : rank[i + 1];
            while (x.next[i] != null && compare(x.next[i].key, key) < 0) {
                rank[i] += x.span[i];
                x = x.next[i];
            }
            update[i] = x;
        }

        Node<K, V> existing = x.next[0];
        if (existing != null && compare(existing.key, key) == 0) {
            V old = existing.value;
            existing.value = value; // not a structural change, so modCount is untouched
            return old;
        }

        int height = levelGenerator.nextLevel(MAX_LEVEL);
        if (height < 1 || height > MAX_LEVEL) {
            throw new IllegalStateException("level generator returned " + height
                    + ", expected a value in [1, " + MAX_LEVEL + "]");
        }
        if (height > level) {
            // Newly activated levels start as a single head pointer spanning the whole list.
            for (int i = level; i < height; i++) {
                rank[i] = 0;
                update[i] = head;
                head.next[i] = null;
                head.span[i] = size;
            }
            level = height;
        }

        Node<K, V> node = new Node<>(key, value, height);
        int position = rank[0]; // entries before the new node
        for (int i = 0; i < height; i++) {
            node.next[i] = update[i].next[i];
            update[i].next[i] = node;
            // update[i] used to jump span[i] steps; the new node now sits (position - rank[i] + 1)
            // steps after it, and inherits the remainder of the old jump.
            node.span[i] = update[i].span[i] - (position - rank[i]);
            update[i].span[i] = (position - rank[i]) + 1;
        }
        for (int i = height; i < level; i++) {
            update[i].span[i]++; // taller pointers now jump over one more entry
        }

        size++;
        modCount++;
        return null;
    }

    @Override
    public V remove(Object key) {
        Node<K, V> removed = unlink(key);
        return removed == null ? null : removed.value;
    }

    @Override
    public void clear() {
        for (int i = 0; i < MAX_LEVEL; i++) {
            head.next[i] = null;
            head.span[i] = 0;
        }
        level = 1;
        size = 0;
        modCount++;
    }

    public Comparator<? super K> comparator() {
        return comparator;
    }

    // ---------------------------------------------------------------------------------------
    // Ordered navigation (all expected O(log n))
    // ---------------------------------------------------------------------------------------

    /** @throws NoSuchElementException if the map is empty */
    public K firstKey() {
        return requireNonEmpty(head.next[0]).key;
    }

    /** @throws NoSuchElementException if the map is empty */
    public K lastKey() {
        return requireNonEmpty(lastNode()).key;
    }

    /** The smallest entry, or {@code null} if empty. Returned entries are immutable snapshots. */
    public Map.Entry<K, V> firstEntry() {
        return snapshot(head.next[0]);
    }

    /** The largest entry, or {@code null} if empty. */
    public Map.Entry<K, V> lastEntry() {
        return snapshot(lastNode());
    }

    /** The greatest entry with key {@code <= key}, or {@code null}. */
    public Map.Entry<K, V> floorEntry(K key) {
        return snapshot(dataNodeOrNull(lastBefore(key, true)));
    }

    /** The greatest entry with key {@code < key}, or {@code null}. */
    public Map.Entry<K, V> lowerEntry(K key) {
        return snapshot(dataNodeOrNull(lastBefore(key, false)));
    }

    /** The least entry with key {@code >= key}, or {@code null}. */
    public Map.Entry<K, V> ceilingEntry(K key) {
        return snapshot(lastBefore(key, false).next[0]);
    }

    /** The least entry with key {@code > key}, or {@code null}. */
    public Map.Entry<K, V> higherEntry(K key) {
        return snapshot(lastBefore(key, true).next[0]);
    }

    public K floorKey(K key) {
        return keyOrNull(floorEntry(key));
    }

    public K lowerKey(K key) {
        return keyOrNull(lowerEntry(key));
    }

    public K ceilingKey(K key) {
        return keyOrNull(ceilingEntry(key));
    }

    public K higherKey(K key) {
        return keyOrNull(higherEntry(key));
    }

    /** Removes and returns the smallest entry, or {@code null} if empty. */
    public Map.Entry<K, V> pollFirstEntry() {
        Node<K, V> first = head.next[0];
        if (first == null) {
            return null;
        }
        Map.Entry<K, V> entry = snapshot(first);
        unlink(first.key);
        return entry;
    }

    // ---------------------------------------------------------------------------------------
    // Order statistics (expected O(log n), thanks to spans)
    // ---------------------------------------------------------------------------------------

    /**
     * The number of keys strictly less than {@code key} — i.e. the 0-based index {@code key}
     * has, or would have if inserted.
     */
    public int rank(K key) {
        return countBefore(key, false);
    }

    /**
     * The entry at 0-based position {@code index} in key order.
     *
     * @throws IndexOutOfBoundsException unless {@code 0 <= index < size()}
     */
    public Map.Entry<K, V> select(int index) {
        Objects.checkIndex(index, size);
        int target = index + 1; // spans count 1-based positions
        int traversed = 0;
        Node<K, V> x = head;
        for (int i = level - 1; i >= 0; i--) {
            while (x.next[i] != null && traversed + x.span[i] <= target) {
                traversed += x.span[i];
                x = x.next[i];
            }
            if (traversed == target) {
                return snapshot(x);
            }
        }
        throw new AssertionError("span bookkeeping is corrupt: could not reach index " + index);
    }

    // ---------------------------------------------------------------------------------------
    // Range queries
    // ---------------------------------------------------------------------------------------

    /**
     * A lazy, read-only view of the entries whose keys fall in {@code range}. The view reflects
     * later changes to the map; its iterator is fail-fast.
     *
     * @throws IllegalArgumentException if the range's lower bound is above its upper bound
     */
    public RangeView range(Range<K> range) {
        Objects.requireNonNull(range, "range");
        if (range.hasLower() && range.hasUpper() && compare(range.lower(), range.upper()) > 0) {
            throw new IllegalArgumentException("lower bound is above upper bound: " + range);
        }
        return new RangeView(range);
    }

    /** Live view over a key interval; see {@link SkipListMap#range(Range)}. */
    public final class RangeView implements Iterable<Map.Entry<K, V>> {
        private final Range<K> range;

        private RangeView(Range<K> range) {
            this.range = range;
        }

        public Range<K> bounds() {
            return range;
        }

        /** Number of entries in the range, computed from two rank lookups — no iteration. */
        public int size() {
            int from = range.hasLower() ? countBefore(range.lower(), !range.lowerInclusive()) : 0;
            int to = range.hasUpper() ? countBefore(range.upper(), range.upperInclusive()) : SkipListMap.this.size;
            return Math.max(0, to - from);
        }

        public boolean isEmpty() {
            return size() == 0;
        }

        @Override
        public Iterator<Map.Entry<K, V>> iterator() {
            Node<K, V> start = range.hasLower()
                    ? lastBefore(range.lower(), !range.lowerInclusive()).next[0]
                    : head.next[0];
            return new EntryIterator(start, range);
        }

        public Stream<Map.Entry<K, V>> stream() {
            Spliterator<Map.Entry<K, V>> spliterator = Spliterators.spliterator(
                    iterator(), size(), Spliterator.ORDERED | Spliterator.DISTINCT | Spliterator.NONNULL);
            return StreamSupport.stream(spliterator, false);
        }

        /** The keys in the range, in order, copied into a new list. */
        public List<K> keys() {
            List<K> keys = new ArrayList<>(size());
            for (Map.Entry<K, V> entry : this) {
                keys.add(entry.getKey());
            }
            return keys;
        }
    }

    // ---------------------------------------------------------------------------------------
    // Views and iteration
    // ---------------------------------------------------------------------------------------

    /**
     * Entries in ascending key order. {@code setValue} on an iterated entry writes through, and
     * {@code Iterator.remove} is supported.
     */
    @Override
    public Set<Map.Entry<K, V>> entrySet() {
        Set<Map.Entry<K, V>> view = entrySet;
        if (view == null) {
            view = new AbstractSet<>() {
                @Override
                public Iterator<Map.Entry<K, V>> iterator() {
                    return new EntryIterator(head.next[0], Range.all());
                }

                @Override
                public int size() {
                    return size;
                }

                @Override
                public void clear() {
                    SkipListMap.this.clear();
                }
            };
            entrySet = view;
        }
        return view;
    }

    /** A structural snapshot for diagnostics and the benchmark. O(n). */
    public SkipListStats stats() {
        List<Integer> perLevel = new ArrayList<>(level);
        long pointers = 0;
        for (int i = 0; i < level; i++) {
            int count = 0;
            for (Node<K, V> x = head.next[i]; x != null; x = x.next[i]) {
                count++;
            }
            perLevel.add(count);
            pointers += count;
        }
        return new SkipListStats(size, level, pointers, perLevel);
    }

    /**
     * Walks a range on level 0, stopping at the first key past the upper bound. Supports
     * {@code remove()} by delegating to the map and re-synchronising the expected mod count.
     */
    private final class EntryIterator implements Iterator<Map.Entry<K, V>> {
        private final Range<K> range;
        private Node<K, V> next;
        private Node<K, V> lastReturned;
        private int expectedModCount = modCount;

        EntryIterator(Node<K, V> start, Range<K> range) {
            this.range = range;
            this.next = withinUpper(start) ? start : null;
        }

        @Override
        public boolean hasNext() {
            return next != null;
        }

        @Override
        public Map.Entry<K, V> next() {
            checkForComodification();
            if (next == null) {
                throw new NoSuchElementException();
            }
            lastReturned = next;
            Node<K, V> candidate = next.next[0];
            next = withinUpper(candidate) ? candidate : null;
            return lastReturned;
        }

        @Override
        public void remove() {
            if (lastReturned == null) {
                throw new IllegalStateException("next() has not been called, or remove() already was");
            }
            checkForComodification();
            // Unlinking lastReturned leaves its successor (our `next`) untouched.
            unlink(lastReturned.key);
            lastReturned = null;
            expectedModCount = modCount;
        }

        private boolean withinUpper(Node<K, V> node) {
            if (node == null) {
                return false;
            }
            if (!range.hasUpper()) {
                return true;
            }
            int c = compare(node.key, range.upper());
            return c < 0 || (c == 0 && range.upperInclusive());
        }

        private void checkForComodification() {
            if (modCount != expectedModCount) {
                throw new ConcurrentModificationException();
            }
        }
    }

    // ---------------------------------------------------------------------------------------
    // Internals
    // ---------------------------------------------------------------------------------------

    /**
     * The last node whose key is {@code < key} ({@code inclusive = false}) or {@code <= key}
     * ({@code inclusive = true}); the head sentinel if there is none. Every navigation method
     * is a thin wrapper over this one search.
     */
    private Node<K, V> lastBefore(K key, boolean inclusive) {
        Objects.requireNonNull(key, "key");
        Node<K, V> x = head;
        for (int i = level - 1; i >= 0; i--) {
            while (x.next[i] != null && precedes(x.next[i].key, key, inclusive)) {
                x = x.next[i];
            }
        }
        return x;
    }

    /** Same search as {@link #lastBefore}, but accumulates spans to count the nodes passed. */
    private int countBefore(K key, boolean inclusive) {
        Objects.requireNonNull(key, "key");
        int count = 0;
        Node<K, V> x = head;
        for (int i = level - 1; i >= 0; i--) {
            while (x.next[i] != null && precedes(x.next[i].key, key, inclusive)) {
                count += x.span[i];
                x = x.next[i];
            }
        }
        return count;
    }

    private boolean precedes(K candidate, K key, boolean inclusive) {
        int c = compare(candidate, key);
        return c < 0 || (inclusive && c == 0);
    }

    @SuppressWarnings("unchecked")
    private Node<K, V> findNode(Object key) {
        Objects.requireNonNull(key, "key");
        // The cast is unchecked; a key of the wrong type fails in compare() with a
        // ClassCastException, exactly as the Map contract allows.
        K k = (K) key;
        Node<K, V> candidate = lastBefore(k, false).next[0];
        return candidate != null && compare(candidate.key, k) == 0 ? candidate : null;
    }

    /** Unlinks the node holding {@code key} from every level, repairing spans. */
    @SuppressWarnings("unchecked")
    private Node<K, V> unlink(Object key) {
        Objects.requireNonNull(key, "key");
        K k = (K) key;
        Node<K, V>[] update = newNodeArray(MAX_LEVEL);
        Node<K, V> x = head;
        for (int i = level - 1; i >= 0; i--) {
            while (x.next[i] != null && compare(x.next[i].key, k) < 0) {
                x = x.next[i];
            }
            update[i] = x;
        }

        Node<K, V> target = x.next[0];
        if (target == null || compare(target.key, k) != 0) {
            return null;
        }
        for (int i = 0; i < level; i++) {
            if (update[i].next[i] == target) {
                // The predecessor now jumps over the target and everything the target jumped.
                update[i].span[i] += target.span[i] - 1;
                update[i].next[i] = target.next[i];
            } else {
                update[i].span[i]--; // a taller pointer passes over one entry fewer
            }
        }
        while (level > 1 && head.next[level - 1] == null) {
            level--;
        }
        size--;
        modCount++;
        return target;
    }

    private Node<K, V> lastNode() {
        Node<K, V> x = head;
        for (int i = level - 1; i >= 0; i--) {
            while (x.next[i] != null) {
                x = x.next[i];
            }
        }
        return x == head ? null : x;
    }

    private Node<K, V> dataNodeOrNull(Node<K, V> node) {
        return node == head ? null : node;
    }

    @SuppressWarnings("unchecked")
    private int compare(K a, K b) {
        return comparator == null
                ? ((Comparable<? super K>) a).compareTo(b)
                : comparator.compare(a, b);
    }

    @SuppressWarnings("unchecked")
    private static <K, V> Node<K, V>[] newNodeArray(int length) {
        return (Node<K, V>[]) new Node<?, ?>[length];
    }

    private static <K, V> Node<K, V> requireNonEmpty(Node<K, V> node) {
        if (node == null) {
            throw new NoSuchElementException("map is empty");
        }
        return node;
    }

    private static <K, V> Map.Entry<K, V> snapshot(Node<K, V> node) {
        return node == null ? null : new AbstractMap.SimpleImmutableEntry<>(node.key, node.value);
    }

    private static <K> K keyOrNull(Map.Entry<K, ?> entry) {
        return entry == null ? null : entry.getKey();
    }

    /**
     * Verifies every structural invariant; used by the tests after random operation sequences.
     * O(n * levels).
     *
     * @throws IllegalStateException describing the first violation found
     */
    void checkInvariants() {
        // Level 0: strictly increasing keys, length == size; remember each node's 1-based position.
        Map<Node<K, V>, Integer> position = new IdentityHashMap<>();
        int count = 0;
        K previous = null;
        for (Node<K, V> x = head.next[0]; x != null; x = x.next[0]) {
            if (previous != null && compare(previous, x.key) >= 0) {
                throw new IllegalStateException("level 0 out of order at " + x.key);
            }
            previous = x.key;
            position.put(x, ++count);
        }
        if (count != size) {
            throw new IllegalStateException("size " + size + " but level 0 has " + count + " nodes");
        }
        if (level < 1 || level > MAX_LEVEL || (level > 1 && head.next[level - 1] == null)) {
            throw new IllegalStateException("bad level " + level);
        }
        // Higher levels: subsequences of level 0 whose spans equal the positional distance.
        for (int i = 0; i < level; i++) {
            int from = 0;
            for (Node<K, V> x = head; ; x = x.next[i]) {
                Node<K, V> next = x.next[i];
                int to = next == null ? size : position.get(next);
                if (x.span[i] != to - from) {
                    throw new IllegalStateException("span at level " + i + " after position " + from
                            + " is " + x.span[i] + ", expected " + (to - from));
                }
                if (next == null) {
                    break;
                }
                if (next.next.length <= i) {
                    throw new IllegalStateException("node " + next.key + " linked above its height");
                }
                from = to;
            }
        }
    }

    /** A data node, or the head sentinel (null key). Doubles as the iterator's entry. */
    private static final class Node<K, V> implements Map.Entry<K, V> {
        final K key;
        V value;
        final Node<K, V>[] next;
        /** {@code span[i]}: level-0 steps covered by {@code next[i]} (to the end if null). */
        final int[] span;

        Node(K key, V value, int height) {
            this.key = key;
            this.value = value;
            this.next = newNodeArray(height);
            this.span = new int[height];
        }

        @Override
        public K getKey() {
            return key;
        }

        @Override
        public V getValue() {
            return value;
        }

        @Override
        public V setValue(V newValue) {
            V old = value;
            value = newValue;
            return old;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Map.Entry<?, ?> e
                    && Objects.equals(key, e.getKey())
                    && Objects.equals(value, e.getValue());
        }

        @Override
        public int hashCode() {
            return Objects.hashCode(key) ^ Objects.hashCode(value);
        }

        @Override
        public String toString() {
            return key + "=" + value;
        }
    }
}
