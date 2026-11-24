package dev.omar.skiplist;

import java.util.List;

/**
 * A structural snapshot of a {@link SkipListMap}, useful for checking that the level generator
 * behaves (each level should hold roughly {@code p} times the nodes of the one below it).
 *
 * @param size           number of entries
 * @param levels         number of levels currently in use (at least 1)
 * @param forwardPointers total forward pointers across all data nodes (memory overhead)
 * @param nodesPerLevel  {@code nodesPerLevel.get(i)} = how many nodes reach level {@code i}
 */
public record SkipListStats(int size, int levels, long forwardPointers, List<Integer> nodesPerLevel) {

    public SkipListStats {
        nodesPerLevel = List.copyOf(nodesPerLevel);
    }

    /** Average forward pointers per entry; about {@code 1 / (1 - p)} for a healthy list. */
    public double pointersPerEntry() {
        return size == 0 ? 0.0 : (double) forwardPointers / size;
    }
}
