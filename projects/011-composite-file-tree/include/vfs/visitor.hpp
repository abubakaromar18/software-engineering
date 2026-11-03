// Visitor pattern: new operations over the tree without touching Node types.
#pragma once

namespace vfs {

class File;
class Directory;

/// Hierarchical visitor.
///
/// Directory::accept drives the traversal (pre-order, children in name
/// order) and calls back into the visitor:
///
///   enter_directory(d)  -> return false to skip d's children
///   ...children...
///   leave_directory(d)  -> only called if enter_directory returned true
///
/// Keeping the walk inside the composite means every visitor gets the same
/// ordering for free, while the enter/leave hooks still let a visitor prune
/// subtrees or track depth.
class NodeVisitor {
public:
    virtual ~NodeVisitor() = default;

    virtual void visit_file(const File& file) = 0;
    virtual bool enter_directory(const Directory& /*dir*/) { return true; }
    virtual void leave_directory(const Directory& /*dir*/) {}

protected:
    NodeVisitor() = default;
    NodeVisitor(const NodeVisitor&) = default;
    NodeVisitor& operator=(const NodeVisitor&) = default;
};

}  // namespace vfs
