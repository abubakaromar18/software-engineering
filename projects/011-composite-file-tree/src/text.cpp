#include "vfs/text.hpp"

#include <array>
#include <format>

namespace vfs {

bool glob_match(std::string_view pattern, std::string_view text) noexcept {
    // Greedy matching with a single backtrack point: on mismatch, return to
    // the most recent '*' and let it swallow one more character.
    std::size_t p = 0;
    std::size_t t = 0;
    std::size_t star = std::string_view::npos;
    std::size_t resume = 0;

    while (t < text.size()) {
        if (p < pattern.size() && (pattern[p] == '?' || pattern[p] == text[t])) {
            ++p;
            ++t;
        } else if (p < pattern.size() && pattern[p] == '*') {
            star = p++;
            resume = t;
        } else if (star != std::string_view::npos) {
            p = star + 1;
            t = ++resume;
        } else {
            return false;
        }
    }
    while (p < pattern.size() && pattern[p] == '*') ++p;
    return p == pattern.size();
}

std::string human_size(std::uint64_t bytes) {
    static constexpr std::array<std::string_view, 7> units{"B",   "KiB", "MiB", "GiB",
                                                           "TiB", "PiB", "EiB"};
    if (bytes < 1024) {
        return std::format("{} B", bytes);
    }
    auto value = static_cast<double>(bytes);
    std::size_t unit = 0;
    while (value >= 1024.0 && unit + 1 < units.size()) {
        value /= 1024.0;
        ++unit;
    }
    return std::format("{:.1f} {}", value, units[unit]);
}

}  // namespace vfs
