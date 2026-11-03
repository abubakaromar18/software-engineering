#include "vfs/manifest.hpp"

#include <charconv>
#include <string_view>
#include <vector>

namespace vfs {

namespace {

constexpr std::string_view kWhitespace = " \t\r";

std::string_view trim(std::string_view s) noexcept {
    const auto first = s.find_first_not_of(kWhitespace);
    if (first == std::string_view::npos) return {};
    const auto last = s.find_last_not_of(kWhitespace);
    return s.substr(first, last - first + 1);
}

std::vector<std::string_view> split_path(std::string_view path) {
    std::vector<std::string_view> parts;
    while (!path.empty()) {
        const auto slash = path.find('/');
        const auto part = path.substr(0, slash);
        if (!part.empty()) parts.push_back(part);
        if (slash == std::string_view::npos) break;
        path.remove_prefix(slash + 1);
    }
    return parts;
}

std::uint64_t parse_size(std::string_view text, std::size_t line) {
    std::uint64_t value = 0;
    const auto* end = text.data() + text.size();
    const auto [ptr, ec] = std::from_chars(text.data(), end, value);
    if (ec == std::errc::result_out_of_range) {
        throw ManifestError(line, "size out of range: '" + std::string{text} + "'");
    }
    if (ec != std::errc{} || ptr != end) {
        throw ManifestError(line, "invalid size: '" + std::string{text} + "'");
    }
    return value;
}

/// Applies one non-empty, non-comment line to the tree.
void apply_line(Directory& root, std::string_view entry, std::size_t line) {
    const auto gap = entry.find_first_of(kWhitespace);
    const std::string_view path = entry.substr(0, gap);
    const std::string_view rest =
        gap == std::string_view::npos ? std::string_view{} : trim(entry.substr(gap));

    const bool is_dir = path.ends_with('/');
    const auto parts = split_path(path);
    if (parts.empty()) {
        throw ManifestError(line, "empty path");
    }
    if (is_dir && !rest.empty()) {
        throw ManifestError(line, "directory entries take no size");
    }
    if (!is_dir && rest.empty()) {
        throw ManifestError(line, "missing size for file '" + std::string{path} + "'");
    }

    try {
        Directory* current = &root;
        const std::size_t dir_parts = is_dir ? parts.size() : parts.size() - 1;
        for (std::size_t i = 0; i < dir_parts; ++i) {
            current = &current->ensure_directory(parts[i]);
        }
        if (!is_dir) {
            current->emplace<File>(std::string{parts.back()}, parse_size(rest, line));
        }
    } catch (const std::invalid_argument& e) {
        // Re-throw domain errors from the tree with line context attached.
        throw ManifestError(line, e.what());
    }
}

}  // namespace

ManifestError::ManifestError(std::size_t line, const std::string& message)
    : std::runtime_error("line " + std::to_string(line) + ": " + message), line_(line) {}

std::unique_ptr<Directory> parse_manifest(std::istream& in) {
    auto root = Directory::make_root();
    std::string raw;
    std::size_t line = 0;
    while (std::getline(in, raw)) {
        ++line;
        const std::string_view entry = trim(raw);
        if (entry.empty() || entry.starts_with('#')) continue;
        apply_line(*root, entry, line);
    }
    if (in.bad()) {
        throw ManifestError(line, "read error");
    }
    return root;
}

}  // namespace vfs
