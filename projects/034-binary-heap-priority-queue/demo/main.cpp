// main.cpp — runs a scripted workload through the Scheduler and prints a
// dispatch log. A low-priority report competes with a steady stream of
// higher-priority API requests. With aging it gets promoted until it runs;
// with --no-aging it starves until the stream stops.
//
// Usage: heap_scheduler [--aging N | --no-aging] [--ticks N]

#include <charconv>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#include "scheduler.hpp"

namespace {

struct Options {
    scheduler::Tick aging_threshold = 3;
    int stream_ticks = 8;  // how many ticks keep submitting API requests
};

constexpr std::string_view kUsage = "usage: heap_scheduler [--aging N | --no-aging] [--ticks N]\n";

unsigned long parse_count(std::string_view flag, const char* text) {
    if (text == nullptr) throw std::invalid_argument(std::string(flag) + " needs a value");
    const std::string_view sv(text);
    unsigned long value = 0;
    const auto [end, ec] = std::from_chars(sv.data(), sv.data() + sv.size(), value);
    if (ec != std::errc{} || end != sv.data() + sv.size()) {
        throw std::invalid_argument(std::string(flag) + " expects a non-negative integer, got '" + text + "'");
    }
    return value;
}

Options parse_args(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string_view arg(argv[i]);
        if (arg == "--aging") {
            options.aging_threshold = parse_count(arg, i + 1 < argc ? argv[++i] : nullptr);
        } else if (arg == "--no-aging") {
            options.aging_threshold = 0;
        } else if (arg == "--ticks") {
            options.stream_ticks = static_cast<int>(parse_count(arg, i + 1 < argc ? argv[++i] : nullptr));
        } else {
            throw std::invalid_argument("unknown argument '" + std::string(arg) + "'");
        }
    }
    return options;
}

void print_dispatch(const scheduler::Task& task, scheduler::Tick now) {
    std::cout << std::setw(4) << now << "  " << std::left << std::setw(18) << task.name << std::right
              << std::setw(4) << task.base_priority << std::setw(6) << task.priority << std::setw(7)
              << (now - 1 - task.submitted_at) << '\n';
}

void run(const Options& options) {
    scheduler::Scheduler sched({.lowest_priority = 9, .aging_threshold = options.aging_threshold});

    sched.submit("backup-db", 5);
    const auto newsletter = sched.submit("send-newsletter", 7);
    sched.submit("nightly-report", 9);
    sched.submit("resize-images", 5);
    const auto logs = sched.submit("rotate-logs", 8);

    sched.escalate(newsletter, 2);  // marketing deadline moved up
    sched.cancel(logs);             // another node already rotated them

    std::cout << "aging: "
              << (options.aging_threshold == 0 ? std::string("off")
                                               : "every " + std::to_string(options.aging_threshold) + " ticks")
              << ", API stream for " << options.stream_ticks << " ticks\n\n"
              << "tick  task              base  prio  waited\n"
              << "----  ----------------  ----  ----  ------\n";

    for (int tick = 0; sched.pending() > 0 || tick < options.stream_ticks; ++tick) {
        if (tick < options.stream_ticks) sched.submit("api-request-" + std::to_string(tick), 3);
        if (auto task = sched.dispatch()) print_dispatch(*task, sched.now());
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        run(parse_args(argc, argv));
    } catch (const std::invalid_argument& e) {
        std::cerr << "error: " << e.what() << '\n' << kUsage;
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
