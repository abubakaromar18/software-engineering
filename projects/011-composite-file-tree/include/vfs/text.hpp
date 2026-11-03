// Small, pure text utilities used by the visitors and the CLI.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>

namespace vfs {

/// Shell-style wildcard match: '*' matches any run of characters (including
/// none), '?' matches exactly one. Everything else is literal and
/// case-sensitive. Runs in O(|pattern| * |text|) worst case, no recursion.
[[nodiscard]] bool glob_match(std::string_view pattern, std::string_view text) noexcept;

/// Formats a byte count with binary units: "512 B", "1.5 KiB", "2.0 GiB".
[[nodiscard]] std::string human_size(std::uint64_t bytes);

}  // namespace vfs
