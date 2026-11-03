// Composite pattern: a virtual filesystem made of Files (leaves) and
// Directories (composites) that share one Node interface.
#pragma once

#include <concepts>
#include <cstdint>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace vfs {

class Directory;
class NodeVisitor;

/// Common interface for every element of the tree.
///
/// Nodes are owned by their parent Directory (via unique_ptr) and keep a
/// non-owning back-pointer to it so they can report their absolute path.
/// Nodes are neither copyable nor movable: moving one would leave the
/// children's parent pointers dangling.
class Node {
public:
    virtual ~Node() = default;

    Node(const Node&) = delete;
    Node& operator=(const Node&) = delete;
    Node(Node&&) = delete;
    Node& operator=(Node&&) = delete;

    [[nodiscard]] const std::string& name() const noexcept { return name_; }
    [[nodiscard]] const Directory* parent() const noexcept { return parent_; }

    /// Absolute path such as "/src/main.cpp"; the root is "/".
    [[nodiscard]] std::string path() const;

    /// Number of edges between this node and the root (root depth is 0).
    [[nodiscard]] std::size_t depth() const noexcept;

    /// Total size in bytes. For a Directory this is the recursive sum of its
    /// children — the operation the Composite pattern lets callers apply
    /// uniformly without knowing whether they hold a leaf or a branch.
    [[nodiscard]] virtual std::uint64_t size() const noexcept = 0;

    [[nodiscard]] virtual bool is_directory() const noexcept = 0;

    /// Double dispatch entry point for the Visitor pattern.
    virtual void accept(NodeVisitor& visitor) const = 0;

protected:
    explicit Node(std::string name) : name_(std::move(name)) {}

private:
    friend class Directory;  // only a Directory may adopt a node
    std::string name_;
    const Directory* parent_ = nullptr;
};

/// Leaf: a file with a fixed size.
class File final : public Node {
public:
    /// @throws std::invalid_argument if `name` is not a valid entry name.
    File(std::string name, std::uint64_t size_bytes);

    [[nodiscard]] std::uint64_t size() const noexcept override { return size_; }
    [[nodiscard]] bool is_directory() const noexcept override { return false; }
    void accept(NodeVisitor& visitor) const override;

    /// Extension without the dot ("cpp" for "main.cpp"), empty if none.
    /// Dotfiles such as ".gitignore" are treated as having no extension.
    [[nodiscard]] std::string_view extension() const noexcept;

private:
    std::uint64_t size_;
};

/// Composite: a directory that owns an ordered set of child nodes.
///
/// Children are kept sorted by name so lookups are O(log n) and every
/// traversal (and therefore every printed tree) is deterministic.
class Directory final : public Node {
public:
    /// @throws std::invalid_argument if `name` is not a valid entry name.
    explicit Directory(std::string name);

    /// Creates the nameless root directory, whose path is "/".
    [[nodiscard]] static std::unique_ptr<Directory> make_root();

    /// Takes ownership of `child` and returns a reference to it.
    /// @throws std::invalid_argument on a null child or a duplicate name.
    Node& add(std::unique_ptr<Node> child);

    /// Constructs a child in place: `dir.emplace<File>("a.txt", 10)`.
    template <std::derived_from<Node> T, typename... Args>
    T& emplace(Args&&... args) {
        return static_cast<T&>(add(std::make_unique<T>(std::forward<Args>(args)...)));
    }

    /// Returns the child directory `name`, creating it if absent.
    /// @throws std::invalid_argument if a *file* with that name exists.
    Directory& ensure_directory(std::string_view name);

    [[nodiscard]] const Node* find_child(std::string_view name) const noexcept;
    [[nodiscard]] Node* find_child(std::string_view name) noexcept;

    /// Resolves a relative path like "src/core/a.cpp" below this directory.
    [[nodiscard]] const Node* resolve(std::string_view relative_path) const noexcept;

    [[nodiscard]] std::span<const std::unique_ptr<Node>> children() const noexcept {
        return children_;
    }
    [[nodiscard]] bool empty() const noexcept { return children_.empty(); }

    [[nodiscard]] std::uint64_t size() const noexcept override;
    [[nodiscard]] bool is_directory() const noexcept override { return true; }
    void accept(NodeVisitor& visitor) const override;

private:
    struct RootTag {};
    explicit Directory(RootTag) : Node(std::string{}) {}

    std::vector<std::unique_ptr<Node>> children_;
};

/// True if `name` can be used for a file or directory entry.
[[nodiscard]] bool is_valid_name(std::string_view name) noexcept;

}  // namespace vfs
