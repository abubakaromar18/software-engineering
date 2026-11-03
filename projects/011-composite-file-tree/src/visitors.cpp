#include "vfs/visitors.hpp"

#include <algorithm>
#include <format>
#include <utility>

#include "vfs/text.hpp"

namespace vfs {

namespace {

bool is_last_child(const Node& node) noexcept {
    const Directory* parent = node.parent();
    return parent == nullptr || parent->children().back().get() == &node;
}

}  // namespace

// ---- TreePrinter -------------------------------------------------------------

TreePrinter::TreePrinter(std::ostream& out, PrintOptions options)
    : out_(out), options_(options) {}

void TreePrinter::print_line(const Node& node, std::string_view label) {
    if (&node != top_) {
        for (const bool ancestor_was_last : last_flags_) {
            out_ << (ancestor_was_last ? "    " : "│   ");
        }
        out_ << (is_last_child(node) ? "└── " : "├── ");
    }
    out_ << label;
    if (options_.show_sizes) {
        out_ << " (" << human_size(node.size()) << ')';
    }
    out_ << '\n';
}

void TreePrinter::visit_file(const File& file) {
    if (top_ == nullptr) top_ = &file;  // printing a lone file is allowed
    print_line(file, file.name());
}

bool TreePrinter::enter_directory(const Directory& dir) {
    if (top_ == nullptr) {
        top_ = &dir;
        print_line(dir, dir.path());
        return true;
    }
    print_line(dir, dir.name() + "/");

    const std::size_t relative_depth = last_flags_.size() + 1;
    if (options_.max_depth != 0 && relative_depth >= options_.max_depth) {
        return false;  // shown, but not expanded
    }
    last_flags_.push_back(is_last_child(dir));
    return true;
}

void TreePrinter::leave_directory(const Directory& dir) {
    if (&dir != top_) last_flags_.pop_back();
}

// ---- FindVisitor -------------------------------------------------------------

FindVisitor::FindVisitor(Predicate predicate) : predicate_(std::move(predicate)) {}

void FindVisitor::visit_file(const File& file) {
    if (predicate_(file)) matches_.push_back(&file);
}

bool FindVisitor::enter_directory(const Directory& dir) {
    if (predicate_(dir)) matches_.push_back(&dir);
    return true;
}

std::vector<const Node*> find(const Node& start, Predicate predicate) {
    FindVisitor finder(std::move(predicate));
    start.accept(finder);
    return finder.matches();
}

namespace match {

Predicate name_glob(std::string pattern) {
    return [pattern = std::move(pattern)](const Node& n) { return glob_match(pattern, n.name()); };
}

Predicate min_size(std::uint64_t bytes) {
    return [bytes](const Node& n) { return n.size() >= bytes; };
}

Predicate files_only() {
    return [](const Node& n) { return !n.is_directory(); };
}

Predicate directories_only() {
    return [](const Node& n) { return n.is_directory(); };
}

Predicate all_of(std::vector<Predicate> predicates) {
    return [predicates = std::move(predicates)](const Node& n) {
        return std::ranges::all_of(predicates, [&n](const Predicate& p) { return p(n); });
    };
}

}  // namespace match

// ---- StatsVisitor ------------------------------------------------------------

void StatsVisitor::visit_file(const File& file) {
    ++files_;
    bytes_ += file.size();
    max_depth_ = std::max(max_depth_, file.depth());
    if (largest_ == nullptr || file.size() > largest_->size()) {
        largest_ = &file;
    }
    const std::string_view ext = file.extension();
    auto& bucket = by_extension_[ext.empty() ? std::string{"(none)"} : std::string{ext}];
    ++bucket.files;
    bucket.bytes += file.size();
}

bool StatsVisitor::enter_directory(const Directory& dir) {
    ++directories_;
    max_depth_ = std::max(max_depth_, dir.depth());
    return true;
}

void print_report(std::ostream& out, const StatsVisitor& stats) {
    out << std::format("files:        {}\n", stats.file_count());
    out << std::format("directories:  {}\n", stats.directory_count());
    out << std::format("total size:   {} ({} bytes)\n", human_size(stats.total_bytes()),
                       stats.total_bytes());
    out << std::format("max depth:    {}\n", stats.max_depth());
    if (const File* largest = stats.largest_file()) {
        out << std::format("largest file: {} ({})\n", largest->path(),
                           human_size(largest->size()));
    }
    if (stats.by_extension().empty()) return;

    // Sort extensions by total bytes (desc), then name, for a useful ranking.
    std::vector<std::pair<std::string_view, ExtensionStats>> rows(stats.by_extension().begin(),
                                                                  stats.by_extension().end());
    std::ranges::sort(rows, [](const auto& a, const auto& b) {
        return a.second.bytes != b.second.bytes ? a.second.bytes > b.second.bytes
                                                : a.first < b.first;
    });
    out << "by extension:\n";
    for (const auto& [ext, s] : rows) {
        out << std::format("  {:<10} {:>4} file{} {:>10}\n", ext, s.files,
                           s.files == 1 ? " " : "s", human_size(s.bytes));
    }
}

}  // namespace vfs
