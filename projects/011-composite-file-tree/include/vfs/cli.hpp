// Command-line front end, kept separate from main() so it can be tested
// with string streams instead of a real process.
#pragma once

#include <cstdint>
#include <istream>
#include <optional>
#include <ostream>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>

namespace vfs::cli {

struct Options {
    std::string manifest_path;  // "-" means standard input
    std::string start = "/";    // subtree to operate on
    std::optional<std::string> find_glob;
    std::uint64_t min_size = 0;
    bool files_only = false;
    bool stats = false;
    bool show_sizes = true;
    std::size_t max_depth = 0;
    bool help = false;
};

class UsageError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

/// Parses argv (without the program name).
/// @throws UsageError on unknown flags or missing/invalid values.
[[nodiscard]] Options parse_args(std::span<const std::string_view> args);

[[nodiscard]] std::string usage();

/// Executes the command. Returns a process exit code: 0 success,
/// 1 runtime error (bad manifest, missing path), 2 usage error.
/// `stdin_stream` is read when the manifest path is "-".
[[nodiscard]] int run(std::span<const std::string_view> args, std::istream& stdin_stream,
                      std::ostream& out, std::ostream& err);

}  // namespace vfs::cli
