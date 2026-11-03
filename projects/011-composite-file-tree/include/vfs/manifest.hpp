// Builds a tree from a plain-text manifest.
//
// Format, one entry per line:
//
//   # comments and blank lines are ignored
//   src/main.cpp   4096      <- file: path, whitespace, size in bytes
//   docs/                    <- empty directory: path ending in '/'
//
// Intermediate directories are created automatically and a leading '/' is
// optional. Every error carries the 1-based line number it came from.
#pragma once

#include <istream>
#include <memory>
#include <stdexcept>
#include <string>

#include "vfs/node.hpp"

namespace vfs {

class ManifestError : public std::runtime_error {
public:
    ManifestError(std::size_t line, const std::string& message);
    [[nodiscard]] std::size_t line() const noexcept { return line_; }

private:
    std::size_t line_;
};

/// @throws ManifestError on any malformed or conflicting line.
[[nodiscard]] std::unique_ptr<Directory> parse_manifest(std::istream& in);

}  // namespace vfs
