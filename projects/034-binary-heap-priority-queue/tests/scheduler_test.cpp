#include "scheduler.hpp"

#include <gtest/gtest.h>

#include <stdexcept>
#include <string>
#include <vector>

namespace {

using scheduler::Scheduler;

std::vector<std::string> drain_names(Scheduler& sched) {
    std::vector<std::string> names;
    while (auto task = sched.dispatch()) names.push_back(task->name);
    return names;
}

TEST(Scheduler, DispatchesMostUrgentFirst) {
    Scheduler sched;
    sched.submit("low", 8);
    sched.submit("high", 1);
    sched.submit("mid", 4);
    EXPECT_EQ(drain_names(sched), (std::vector<std::string>{"high", "mid", "low"}));
    EXPECT_FALSE(sched.dispatch().has_value());
}

TEST(Scheduler, EqualPrioritiesRunInSubmissionOrder) {
    Scheduler sched;
    for (const char* name : {"a", "b", "c", "d", "e", "f"}) sched.submit(name, 5);
    EXPECT_EQ(drain_names(sched), (std::vector<std::string>{"a", "b", "c", "d", "e", "f"}));
}

TEST(Scheduler, RejectsOutOfRangePriorities) {
    Scheduler sched({.lowest_priority = 3, .aging_threshold = 0});
    EXPECT_THROW(sched.submit("neg", -1), std::invalid_argument);
    EXPECT_THROW(sched.submit("big", 4), std::invalid_argument);
    EXPECT_EQ(sched.pending(), 0u);
}

TEST(Scheduler, RejectsInvalidConfig) {
    EXPECT_THROW(Scheduler({.lowest_priority = -1, .aging_threshold = 0}), std::invalid_argument);
}

TEST(Scheduler, EscalateMovesTaskAhead) {
    Scheduler sched;
    sched.submit("first", 3);
    const auto late = sched.submit("late", 9);
    sched.escalate(late, 0);
    EXPECT_EQ(sched.find(late)->priority, 0);
    EXPECT_EQ(drain_names(sched), (std::vector<std::string>{"late", "first"}));
}

TEST(Scheduler, EscalateValidatesInput) {
    Scheduler sched;
    const auto id = sched.submit("t", 4);
    EXPECT_THROW(sched.escalate(id, 4), std::invalid_argument);   // not more urgent
    EXPECT_THROW(sched.escalate(id, 6), std::invalid_argument);   // less urgent
    EXPECT_THROW(sched.escalate(id, -2), std::invalid_argument);  // out of range
    EXPECT_THROW(sched.escalate(999, 1), std::out_of_range);      // unknown id
}

TEST(Scheduler, CancelRemovesPendingTask) {
    Scheduler sched;
    sched.submit("keep", 2);
    const auto drop = sched.submit("drop", 1);
    EXPECT_TRUE(sched.cancel(drop));
    EXPECT_FALSE(sched.cancel(drop));
    EXPECT_EQ(sched.find(drop), nullptr);
    EXPECT_EQ(drain_names(sched), std::vector<std::string>{"keep"});
}

TEST(Scheduler, ClockAdvancesPerDispatch) {
    Scheduler sched;
    sched.submit("a", 1);
    sched.submit("b", 1);
    EXPECT_EQ(sched.now(), 0u);
    (void)sched.dispatch();
    (void)sched.dispatch();
    (void)sched.dispatch();  // empty: clock does not move
    EXPECT_EQ(sched.now(), 2u);
}

// Feeds one fresh priority-1 task per tick and reports the tick at which
// the priority-9 task finally runs (or 0 if it never ran during the stream).
scheduler::Tick tick_low_priority_task_runs(scheduler::Tick aging_threshold, int stream_length) {
    Scheduler sched({.lowest_priority = 9, .aging_threshold = aging_threshold});
    sched.submit("starving", 9);
    for (int i = 0; i < stream_length; ++i) {
        sched.submit("hot-" + std::to_string(i), 1);
        if (sched.dispatch()->name == "starving") return sched.now();
    }
    return 0;
}

TEST(Scheduler, WithoutAgingLowPriorityTaskStarves) {
    EXPECT_EQ(tick_low_priority_task_runs(0, 100), 0u);
}

TEST(Scheduler, AgingPreventsStarvation) {
    // Promoted one level every 2 ticks: 9 -> 1 takes 16 ticks, and then its
    // older sequence number beats every newer priority-1 task.
    const auto ran_at = tick_low_priority_task_runs(2, 100);
    EXPECT_GT(ran_at, 0u);
    EXPECT_LE(ran_at, 17u);
}

TEST(Scheduler, AgingReportsCurrentAndBasePriority) {
    Scheduler sched({.lowest_priority = 9, .aging_threshold = 1});
    sched.submit("blocker-1", 0);
    sched.submit("blocker-2", 0);
    const auto waiting = sched.submit("waiting", 6);
    (void)sched.dispatch();
    (void)sched.dispatch();
    const auto* task = sched.find(waiting);
    ASSERT_NE(task, nullptr);
    EXPECT_EQ(task->base_priority, 6);
    EXPECT_EQ(task->priority, 4);
}

}  // namespace
