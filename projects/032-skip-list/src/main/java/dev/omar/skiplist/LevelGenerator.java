package dev.omar.skiplist;

/**
 * Chooses the height (number of forward pointers) of a newly inserted skip-list node.
 *
 * <p>The skip list's expected O(log n) performance depends entirely on this choice being
 * random and independent of the keys. Keeping it behind an interface lets tests inject a
 * scripted sequence of heights to build an exact, known shape, while production code uses
 * {@link GeometricLevelGenerator}.
 */
@FunctionalInterface
public interface LevelGenerator {

    /**
     * Returns the height for the next node.
     *
     * @param maxLevel the largest height the list supports (at least 1)
     * @return a height in {@code [1, maxLevel]}
     */
    int nextLevel(int maxLevel);
}
