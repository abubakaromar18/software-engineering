#include <gtest/gtest.h>

#include <sstream>

#include "vfs/manifest.hpp"

using vfs::ManifestError;
using vfs::parse_manifest;

namespace {

std::unique_ptr<vfs::Directory> parse(const std::string& text) {
    std::istringstream in(text);
    return parse_manifest(in);
}

/// Returns the line number reported by the ManifestError `text` produces.
std::size_t error_line(const std::string& text) {
    try {
        parse(text);
    } catch (const ManifestError& e) {
        return e.line();
    }
    ADD_FAILURE() << "expected ManifestError for:\n" << text;
    return 0;
}

}  // namespace

TEST(Manifest, BuildsNestedTree) {
    const auto root = parse(
        "# comment\n"
        "\n"
        "src/main.cpp 100\n"
        "/src/lib/util.cpp\t250\n"
        "docs/\n"
        "  README.md   7  \r\n");

    EXPECT_EQ(root->size(), 357u);
    ASSERT_NE(root->resolve("src/lib/util.cpp"), nullptr);
    EXPECT_EQ(root->resolve("src/lib/util.cpp")->size(), 250u);
    ASSERT_NE(root->resolve("docs"), nullptr);
    EXPECT_TRUE(root->resolve("docs")->is_directory());
    EXPECT_EQ(root->resolve("README.md")->size(), 7u);
}

TEST(Manifest, EmptyInputGivesEmptyRoot) {
    const auto root = parse("");
    EXPECT_TRUE(root->empty());
}

TEST(Manifest, RepeatedDirectoryLinesAreHarmless) {
    const auto root = parse("a/\na/\na/b.txt 1\n");
    EXPECT_EQ(root->children().size(), 1u);
}

TEST(Manifest, ErrorsReportTheOffendingLine) {
    EXPECT_EQ(error_line("ok.txt 1\nmissing-size.txt\n"), 2u);
    EXPECT_EQ(error_line("a.txt 12x\n"), 1u);
    EXPECT_EQ(error_line("a.txt -5\n"), 1u);
    EXPECT_EQ(error_line("a.txt 99999999999999999999999\n"), 1u);
    EXPECT_EQ(error_line("dir/ 10\n"), 1u);
    EXPECT_EQ(error_line("/ \n"), 1u);
    EXPECT_EQ(error_line("a.txt 1 2\n"), 1u);
}

TEST(Manifest, ConflictsBecomeManifestErrors) {
    EXPECT_EQ(error_line("a.txt 1\n\na.txt 2\n"), 3u);         // duplicate file
    EXPECT_EQ(error_line("lib 1\nlib/x.cpp 2\n"), 2u);         // file used as a dir
    EXPECT_EQ(error_line("lib/x.cpp 2\nlib 1\n"), 2u);         // dir clobbered by file
    EXPECT_EQ(error_line("a/../b.txt 1\n"), 1u);               // '..' is not allowed
}

TEST(Manifest, ErrorMessageIncludesLinePrefix) {
    try {
        parse("\n\nbad 1z\n");
        FAIL() << "expected ManifestError";
    } catch (const ManifestError& e) {
        EXPECT_STREQ(e.what(), "line 3: invalid size: '1z'");
    }
}
