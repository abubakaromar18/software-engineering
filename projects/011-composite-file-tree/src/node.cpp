#include "vfs/node.hpp"

#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <utility>
#include <vector>

#include "vfs/visitor.hpp"

namespace vfs {

namespace {

std::string validated(std::string name) {
    if (!is_valid_name(name)) {
        throw std::invalid_argument("invalid entry name: '" + name + "'");
    }
    return name;
}

}  // namespace

bool is_valid_name(std::string_view name) noexcept {
    return !name.empty() && name != "." && name != ".." &&
           name.find('/') == std::string_view::npos &&
           name.find('\0') == std::string_view::npos;
}

// ---- Node ------------------------------------------------------------------

std::string Node::path() const {
    if (parent_ == nullptr) {
        return name_.empty() ? "/" : name_;  // detached nodes report their name
    }
    std::vector<const Node*> chain;
    for (const Node* n = this; n->parent_ != nullptr; n = n->parent_) {
        chain.push_back(n);
    }
    std::string result;
    for (auto it = chain.rbegin(); it != chain.rend(); ++it) {
        result += '/';
        result += (*it)->name_;
    }
    return result;
}

std::size_t Node::depth() const noexcept {
    std::size_t d = 0;
    for (const Node* n = parent_; n != nullptr; n = n->parent_) ++d;
    return d;
}

// ---- File ------------------------------------------------------------------

File::File(std::string name, std::uint64_t size_bytes)
    : Node(validated(std::move(name))), size_(size_bytes) {}

void File::accept(NodeVisitor& visitor) const { visitor.visit_file(*this); }

std::string_view File::extension() const noexcept {
    const std::string_view n = name();
    const auto dot = n.rfind('.');
    if (dot == std::string_view::npos || dot == 0 || dot + 1 == n.size()) {
        return {};
    }
    return n.substr(dot + 1);
}

// ---- Directory -------------------------------------------------------------

Directory::Directory(std::string name) : Node(validated(std::move(name))) {}

std::unique_ptr<Directory> Directory::make_root() {
    // make_unique cannot reach the private constructor.
    return std::unique_ptr<Directory>(new Directory(RootTag{}));
}

Node& Directory::add(std::unique_ptr<Node> child) {
    if (!child) {
        throw std::invalid_argument("cannot add a null node");
    }
    if (child->parent_ != nullptr) {
        throw std::invalid_argument("node '" + child->name() + "' already has a parent");
    }
    const auto pos = std::ranges::lower_bound(children_, std::string_view{child->name()},
                                              std::ranges::less{}, &Node::name);
    if (pos != children_.end() && (*pos)->name() == child->name()) {
        throw std::invalid_argument("'" + path() + "' already contains '" + child->name() + "'");
    }
    child->parent_ = this;
    return **children_.insert(pos, std::move(child));
}

Directory& Directory::ensure_directory(std::string_view name) {
    if (Node* existing = find_child(name)) {
        if (!existing->is_directory()) {
            throw std::invalid_argument("'" + existing->path() + "' is a file, not a directory");
        }
        return static_cast<Directory&>(*existing);
    }
    return emplace<Directory>(std::string{name});
}

const Node* Directory::find_child(std::string_view name) const noexcept {
    const auto pos = std::ranges::lower_bound(children_, name, std::ranges::less{}, &Node::name);
    return (pos != children_.end() && (*pos)->name() == name) ? pos->get() : nullptr;
}

Node* Directory::find_child(std::string_view name) noexcept {
    return const_cast<Node*>(std::as_const(*this).find_child(name));
}

const Node* Directory::resolve(std::string_view relative_path) const noexcept {
    const Node* current = this;
    while (!relative_path.empty()) {
        const auto slash = relative_path.find('/');
        const std::string_view part = relative_path.substr(0, slash);
        relative_path = slash == std::string_view::npos ? std::string_view{}
                                                        : relative_path.substr(slash + 1);
        if (part.empty()) continue;  // tolerate "a//b" and trailing '/'
        if (!current->is_directory()) return nullptr;
        current = static_cast<const Directory*>(current)->find_child(part);
        if (current == nullptr) return nullptr;
    }
    return current;
}

std::uint64_t Directory::size() const noexcept {
    // Recomputed on demand. Caching would make this O(1) but every mutation
    // would then have to invalidate all ancestors; see README trade-offs.
    return std::accumulate(children_.begin(), children_.end(), std::uint64_t{0},
                           [](std::uint64_t acc, const auto& c) { return acc + c->size(); });
}

void Directory::accept(NodeVisitor& visitor) const {
    if (!visitor.enter_directory(*this)) return;
    for (const auto& child : children_) {
        child->accept(visitor);
    }
    visitor.leave_directory(*this);
}

}  // namespace vfs
