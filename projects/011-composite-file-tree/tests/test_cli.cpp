#include <gtest/gtest.h>

#include <sstream>
#include <string>
#include <string_view>
#include <vector>

#include "vfs/cli.hpp"

using vfs::cli::parse_args;
using vfs::cli::UsageError;

namespace {

struct Result {
    int code;
    std::string out;
    std::string err;
};

Result run(std::vector<std::string_view> args, const std::string& stdin_text = "") {
    std::istringstream in(stdin_text);
    std::ostringstream out;
    std::ostringstream err;
    const int code = vfs::cli::run(args, in, out, err);
    return {code, out.str(), err.str()};
}

const std::string kManifest =
    "src/main.cpp 100\n"
    "src/big.cpp 5000\n"
    "notes.txt 20\n";

}  // namespace

TEST(CliArgs, ParsesAllOptions) {
    const std::vector<std::string_view> args{"--find", "*.cpp", "--min-size", "10", "--files",
                                             "--no-sizes", "--at", "/src", "m.txt"};
    const auto opts = parse_args(args);
    EXPECT_EQ(opts.manifest_path, "m.txt");
    EXPECT_EQ(opts.find_glob.value(), "*.cpp");
    EXPECT_EQ(opts.min_size, 10u);
    EXPECT_TRUE(opts.files_only);
    EXPECT_FALSE(opts.show_sizes);
    EXPECT_EQ(opts.start, "/src");
}

TEST(CliArgs, RejectsBadInput) {
    using Args = std::vector<std::string_view>;
    EXPECT_THROW((void)parse_args(Args{}), UsageError);
    EXPECT_THROW((void)parse_args(Args{"--bogus", "m"}), UsageError);
    EXPECT_THROW((void)parse_args(Args{"m", "extra"}), UsageError);
    EXPECT_THROW((void)parse_args(Args{"--depth"}), UsageError);
    EXPECT_THROW((void)parse_args(Args{"--depth", "-1", "m"}), UsageError);
    EXPECT_THROW((void)parse_args(Args{"--min-size", "5", "m"}), UsageError);
}

TEST(Cli, HelpExitsZero) {
    const auto r = run({"--help"});
    EXPECT_EQ(r.code, 0);
    EXPECT_NE(r.out.find("usage:"), std::string::npos);
}

TEST(Cli, UsageErrorExitsTwo) {
    const auto r = run({"--nope", "-"});
    EXPECT_EQ(r.code, 2);
    EXPECT_NE(r.err.find("unknown option: --nope"), std::string::npos);
}

TEST(Cli, PrintsTreeFromStdin) {
    const auto r = run({"--no-sizes", "-"}, kManifest);
    EXPECT_EQ(r.code, 0);
    EXPECT_EQ(r.out,
              "/\n"
              "├── notes.txt\n"
              "└── src/\n"
              "    ├── big.cpp\n"
              "    └── main.cpp\n");
}

TEST(Cli, FindWithFilters) {
    const auto r = run({"--find", "*.cpp", "--min-size", "1000", "-"}, kManifest);
    EXPECT_EQ(r.code, 0);
    EXPECT_EQ(r.out, "/src/big.cpp  4.9 KiB\n");
}

TEST(Cli, StatsOnSubtree) {
    const auto r = run({"--stats", "--at", "src", "-"}, kManifest);
    EXPECT_EQ(r.code, 0);
    EXPECT_NE(r.out.find("files:        2"), std::string::npos);
    EXPECT_EQ(r.out.find("txt"), std::string::npos);
}

TEST(Cli, ManifestErrorExitsOne) {
    const auto r = run({"-"}, "ok 1\nbad\n");
    EXPECT_EQ(r.code, 1);
    EXPECT_EQ(r.err, "error: line 2: missing size for file 'bad'\n");
}

TEST(Cli, UnknownStartPathExitsOne) {
    const auto r = run({"--at", "/nope", "-"}, kManifest);
    EXPECT_EQ(r.code, 1);
    EXPECT_NE(r.err.find("no such path: /nope"), std::string::npos);
}

TEST(Cli, MissingFileExitsOne) {
    const auto r = run({"/definitely/not/here.manifest"});
    EXPECT_EQ(r.code, 1);
    EXPECT_NE(r.err.find("cannot open"), std::string::npos);
}

TEST(Cli, ExampleManifestParses) {
    const auto r = run({"--stats", VFS_EXAMPLE_MANIFEST});
    EXPECT_EQ(r.code, 0) << r.err;
    EXPECT_NE(r.out.find("largest file: /docs/images/tree.png"), std::string::npos);
}
