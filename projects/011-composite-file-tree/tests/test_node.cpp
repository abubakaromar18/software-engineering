#include <gtest/gtest.h>

#include <stdexcept>

#include "vfs/node.hpp"

using vfs::Directory;
using vfs::File;

namespace {

std::unique_ptr<Directory> sample_tree() {
    auto root = Directory::make_root();
    auto& src = root->emplace<Directory>("src");
    src.emplace<File>("main.cpp", 100);
    src.emplace<File>("util.cpp", 250);
    auto& docs = root->emplace<Directory>("docs");
    docs.emplace<File>("guide.md", 50);
    root->emplace<File>("README.md", 10);
    return root;
}

}  // namespace

TEST(Node, FileReportsOwnSize) {
    const File f("a.txt", 42);
    EXPECT_EQ(f.size(), 42u);
    EXPECT_FALSE(f.is_directory());
}

TEST(Node, DirectorySizeIsRecursiveSum) {
    const auto root = sample_tree();
    EXPECT_EQ(root->size(), 410u);
    EXPECT_EQ(root->find_child("src")->size(), 350u);
}

TEST(Node, EmptyDirectoryHasZeroSize) {
    const Directory d("empty");
    EXPECT_EQ(d.size(), 0u);
    EXPECT_TRUE(d.empty());
}

TEST(Node, ChildrenAreKeptSortedByName) {
    const auto root = sample_tree();
    std::vector<std::string> names;
    for (const auto& c : root->children()) names.push_back(c->name());
    EXPECT_EQ(names, (std::vector<std::string>{"README.md", "docs", "src"}));
}

TEST(Node, PathsAreAbsolute) {
    const auto root = sample_tree();
    EXPECT_EQ(root->path(), "/");
    EXPECT_EQ(root->resolve("src/main.cpp")->path(), "/src/main.cpp");
    EXPECT_EQ(root->resolve("docs")->path(), "/docs");
}

TEST(Node, DepthCountsEdgesFromRoot) {
    const auto root = sample_tree();
    EXPECT_EQ(root->depth(), 0u);
    EXPECT_EQ(root->resolve("src")->depth(), 1u);
    EXPECT_EQ(root->resolve("src/util.cpp")->depth(), 2u);
}

TEST(Node, ResolveHandlesEdgeCases) {
    const auto root = sample_tree();
    EXPECT_EQ(root->resolve(""), root.get());
    EXPECT_EQ(root->resolve("/"), root.get());
    EXPECT_NE(root->resolve("/src//main.cpp/"), nullptr);
    EXPECT_EQ(root->resolve("src/missing.cpp"), nullptr);
    EXPECT_EQ(root->resolve("README.md/nested"), nullptr);  // can't descend into a file
}

TEST(Node, AddRejectsDuplicates) {
    auto root = sample_tree();
    EXPECT_THROW(root->emplace<File>("README.md", 1), std::invalid_argument);
    EXPECT_THROW(root->emplace<Directory>("src"), std::invalid_argument);
}

TEST(Node, AddRejectsNull) {
    auto root = Directory::make_root();
    EXPECT_THROW(root->add(nullptr), std::invalid_argument);
}

TEST(Node, InvalidNamesAreRejected) {
    EXPECT_THROW(File("", 1), std::invalid_argument);
    EXPECT_THROW(File("a/b", 1), std::invalid_argument);
    EXPECT_THROW(Directory("."), std::invalid_argument);
    EXPECT_THROW(Directory(".."), std::invalid_argument);
    EXPECT_NO_THROW(File(".hidden", 1));
}

TEST(Node, EnsureDirectoryIsIdempotent) {
    auto root = Directory::make_root();
    Directory& first = root->ensure_directory("lib");
    Directory& second = root->ensure_directory("lib");
    EXPECT_EQ(&first, &second);
    EXPECT_EQ(root->children().size(), 1u);
}

TEST(Node, EnsureDirectoryRefusesToShadowAFile) {
    auto root = Directory::make_root();
    root->emplace<File>("lib", 1);
    EXPECT_THROW(root->ensure_directory("lib"), std::invalid_argument);
}

TEST(Node, ParentPointerIsSetOnAdd) {
    auto root = Directory::make_root();
    auto& dir = root->emplace<Directory>("a");
    auto& file = dir.emplace<File>("b.txt", 3);
    EXPECT_EQ(file.parent(), &dir);
    EXPECT_EQ(dir.parent(), root.get());
    EXPECT_EQ(root->parent(), nullptr);
}

TEST(Node, ExtensionParsing) {
    EXPECT_EQ(File("main.cpp", 0).extension(), "cpp");
    EXPECT_EQ(File("archive.tar.gz", 0).extension(), "gz");
    EXPECT_EQ(File("Makefile", 0).extension(), "");
    EXPECT_EQ(File(".gitignore", 0).extension(), "");
    EXPECT_EQ(File("trailing.", 0).extension(), "");
}
