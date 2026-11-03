// Concrete visitors: each is one self-contained operation over the tree.
#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <ostream>
#include <string>
#include <vector>

#include "vfs/node.hpp"
#include "vfs/visitor.hpp"

namespace vfs {

// ---- Printing ----------------------------------------------------------------

struct PrintOptions {
    bool show_sizes = true;
    /// Maximum directory depth to expand below the starting node; deeper
    /// directories are printed but their contents are not. 0 = unlimited.
    std::size_t max_depth = 0;
};

/// Renders a `tree`-style drawing:
///
///   / (4.2 KiB)
///   ├── docs/ (1.0 KiB)
///   │   └── guide.md (1.0 KiB)
///   └── main.cpp (3.2 KiB)
class TreePrinter final : public NodeVisitor {
public:
    explicit TreePrinter(std::ostream& out, PrintOptions options = {});

    void visit_file(const File& file) override;
    bool enter_directory(const Directory& dir) override;
    void leave_directory(const Directory& dir) override;

private:
    void print_line(const Node& node, std::string_view label);

    std::ostream& out_;
    PrintOptions options_;
    const Node* top_ = nullptr;
    // One entry per expanded directory below the top: was it the last child?
    std::vector<bool> last_flags_;
};

// ---- Searching ---------------------------------------------------------------

using Predicate = std::function<bool(const Node&)>;

/// Collects every node (files and directories) that satisfies a predicate,
/// in traversal order.
class FindVisitor final : public NodeVisitor {
public:
    explicit FindVisitor(Predicate predicate);

    void visit_file(const File& file) override;
    bool enter_directory(const Directory& dir) override;

    [[nodiscard]] const std::vector<const Node*>& matches() const noexcept { return matches_; }

private:
    Predicate predicate_;
    std::vector<const Node*> matches_;
};

/// Predicate factories; combine them with all_of.
namespace match {
[[nodiscard]] Predicate name_glob(std::string pattern);
[[nodiscard]] Predicate min_size(std::uint64_t bytes);
[[nodiscard]] Predicate files_only();
[[nodiscard]] Predicate directories_only();
[[nodiscard]] Predicate all_of(std::vector<Predicate> predicates);
}  // namespace match

/// Convenience wrapper: run a FindVisitor from `start` and return the hits.
[[nodiscard]] std::vector<const Node*> find(const Node& start, Predicate predicate);

// ---- Statistics --------------------------------------------------------------

struct ExtensionStats {
    std::size_t files = 0;
    std::uint64_t bytes = 0;
};

/// Aggregates counts, sizes and an extension histogram in a single pass.
class StatsVisitor final : public NodeVisitor {
public:
    void visit_file(const File& file) override;
    bool enter_directory(const Directory& dir) override;

    [[nodiscard]] std::size_t file_count() const noexcept { return files_; }
    /// Includes the starting directory itself.
    [[nodiscard]] std::size_t directory_count() const noexcept { return directories_; }
    [[nodiscard]] std::uint64_t total_bytes() const noexcept { return bytes_; }
    /// Deepest absolute depth reached (see Node::depth).
    [[nodiscard]] std::size_t max_depth() const noexcept { return max_depth_; }
    /// Largest file seen, or nullptr if there were no files. Ties keep the
    /// first file in traversal order.
    [[nodiscard]] const File* largest_file() const noexcept { return largest_; }
    /// Keyed by extension; files without one are grouped under "(none)".
    [[nodiscard]] const std::map<std::string, ExtensionStats, std::less<>>& by_extension()
        const noexcept {
        return by_extension_;
    }

private:
    std::size_t files_ = 0;
    std::size_t directories_ = 0;
    std::uint64_t bytes_ = 0;
    std::size_t max_depth_ = 0;
    const File* largest_ = nullptr;
    std::map<std::string, ExtensionStats, std::less<>> by_extension_;
};

/// Writes a human-readable summary of `stats`.
void print_report(std::ostream& out, const StatsVisitor& stats);

}  // namespace vfs
