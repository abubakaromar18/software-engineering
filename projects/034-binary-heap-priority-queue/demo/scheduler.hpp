// scheduler.hpp — a single-worker task scheduler built on IndexedHeap.
//
// It shows why decrease-key matters in practice:
//   * escalate() raises a pending task's urgency in O(log n).
//   * cancel() removes a task from the middle of the queue in O(log n).
//   * Aging (optional) prevents starvation: a task that has waited
//     `aging_threshold` dispatches is promoted one level, via decrease_key.
//
// Priorities run from 0 (most urgent) to `lowest_priority`. Tasks with equal
// priority run in submission order. A binary heap is not stable on its own,
// so each task's rank is (priority, submission sequence).
#pragma once

#include <compare>
#include <cstdint>
#include <optional>
#include <string>
#include <unordered_map>

#include "heapq/indexed_heap.hpp"

namespace scheduler {

using TaskId = std::uint64_t;
using Priority = int;
using Tick = std::uint64_t;

struct Task {
    TaskId id = 0;
    std::string name;
    Priority base_priority = 0;  ///< priority at submission (or escalation)
    Priority priority = 0;       ///< current priority, including aging
    Tick submitted_at = 0;       ///< scheduler clock when submitted
};

struct SchedulerConfig {
    Priority lowest_priority = 9;
    /// Dispatches a task may wait before it is promoted one level.
    /// 0 disables aging.
    Tick aging_threshold = 0;
};

class Scheduler {
public:
    /// Throws std::invalid_argument if the config is inconsistent.
    explicit Scheduler(SchedulerConfig config = {});

    /// Queues a task and returns its id. Throws std::invalid_argument for a
    /// priority outside [0, lowest_priority].
    TaskId submit(std::string name, Priority priority);

    /// Makes a pending task more urgent. Throws std::out_of_range for an
    /// unknown id and std::invalid_argument if `priority` is not more urgent
    /// than the task's current priority.
    void escalate(TaskId id, Priority priority);

    /// Removes a pending task. Returns false if it is not pending.
    bool cancel(TaskId id);

    /// Removes and returns the most urgent task, then advances the clock
    /// one tick and applies aging. Returns nullopt when nothing is pending.
    std::optional<Task> dispatch();

    [[nodiscard]] std::size_t pending() const noexcept { return queue_.size(); }
    [[nodiscard]] Tick now() const noexcept { return clock_; }
    [[nodiscard]] const Task* find(TaskId id) const;

private:
    // Lexicographic order: urgency first, then FIFO among equals.
    struct Rank {
        Priority priority;
        std::uint64_t sequence;
        auto operator<=>(const Rank&) const = default;
    };

    struct Pending {
        Task task;
        std::uint64_t sequence;
        Tick waiting_since;  ///< tick of submission or of the last promotion
    };

    void validate_priority(Priority priority) const;
    void apply_aging();

    SchedulerConfig config_;
    heapq::IndexedHeap<TaskId, Rank> queue_;
    std::unordered_map<TaskId, Pending> pending_;
    Tick clock_ = 0;
    TaskId next_id_ = 1;
    std::uint64_t next_sequence_ = 0;
};

}  // namespace scheduler
