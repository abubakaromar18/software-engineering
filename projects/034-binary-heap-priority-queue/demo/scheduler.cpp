#include "scheduler.hpp"

#include <stdexcept>
#include <utility>

namespace scheduler {

Scheduler::Scheduler(SchedulerConfig config) : config_(config) {
    if (config_.lowest_priority < 0) {
        throw std::invalid_argument("lowest_priority must be >= 0");
    }
}

void Scheduler::validate_priority(Priority priority) const {
    if (priority < 0 || priority > config_.lowest_priority) {
        throw std::invalid_argument("priority must be in [0, " + std::to_string(config_.lowest_priority) + "]");
    }
}

TaskId Scheduler::submit(std::string name, Priority priority) {
    validate_priority(priority);
    const TaskId id = next_id_++;
    const std::uint64_t sequence = next_sequence_++;

    Task task{id, std::move(name), priority, priority, clock_};
    queue_.push(id, Rank{priority, sequence});
    pending_.emplace(id, Pending{std::move(task), sequence, clock_});
    return id;
}

void Scheduler::escalate(TaskId id, Priority priority) {
    const auto it = pending_.find(id);
    if (it == pending_.end()) throw std::out_of_range("no pending task with id " + std::to_string(id));
    validate_priority(priority);

    Pending& entry = it->second;
    if (priority >= entry.task.priority) {
        throw std::invalid_argument("escalate() must make a task more urgent");
    }
    // Keep the original sequence: an escalated task still yields to older
    // tasks already at the target level.
    queue_.decrease_key(id, Rank{priority, entry.sequence});
    entry.task.base_priority = priority;
    entry.task.priority = priority;
    entry.waiting_since = clock_;
}

bool Scheduler::cancel(TaskId id) {
    if (!queue_.erase(id)) return false;
    pending_.erase(id);
    return true;
}

std::optional<Task> Scheduler::dispatch() {
    auto next = queue_.try_pop();
    if (!next) return std::nullopt;

    auto node = pending_.extract(next->key);
    ++clock_;
    apply_aging();
    return std::move(node.mapped().task);
}

const Task* Scheduler::find(TaskId id) const {
    const auto it = pending_.find(id);
    return it == pending_.end() ? nullptr : &it->second.task;
}

// O(n log n) per dispatch in the worst case: every pending task is checked
// and each promotion is a decrease_key. Fine for a demo-sized queue; see the
// README for the bucketed alternative.
void Scheduler::apply_aging() {
    if (config_.aging_threshold == 0) return;
    for (auto& [id, entry] : pending_) {
        const bool waited_long_enough = clock_ - entry.waiting_since >= config_.aging_threshold;
        if (!waited_long_enough || entry.task.priority == 0) continue;
        --entry.task.priority;
        entry.waiting_since = clock_;
        queue_.decrease_key(id, Rank{entry.task.priority, entry.sequence});
    }
}

}  // namespace scheduler
