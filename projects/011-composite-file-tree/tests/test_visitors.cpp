#include <gtest/gtest.h>

#include <sstream>
#include <string>
#include <vector>

#include "vfs/node.hpp"
#include "vfs/visitors.hpp"

using namespace vfs;

namespace {

std::unique_ptr<Directory> sample_tree() {
    auto root = Directory::make_root();
    auto& src = root->emplace<Directory>("src");
    src.emplace<File>("main.cpp", 100);
    auto& core = src.emplace<Directory>("core");
    core.emplace<File>("node.cpp", 2048);
    core.emplace<File>("node.hpp", 300);
    root->emplace<Directory>("empty");
    root->emplace<File>("README.md", 10);
    root->emplace<File>("Makefile", 5);
    return root;
}

std::vector<std::string> paths(const std::vector<const Node*>& nodes) {
    std::vector<std::string> out;
    for (const Node* n : nodes) out.push_back(n->path());
    return out;
}

/// Records the callback sequence to pin down traversal order.
class RecordingVisitor final : public NodeVisitor {
public:
    std::vector<std::string> events;
    std::string skip;  // path of a directory whose children should be skipped

    void visit_file(const File& f) override { events.push_back("file " + f.name()); }
    bool enter_directory(const Directory& d) override {
        events.push_back("enter " + d.path());
        return d.path() != skip;
    }
    void leave_directory(const Directory& d) override { events.push_back("leave " + d.path()); }
};

}  // namespace

// ---- Traversal ---------------------------------------------------------------

TEST(Traversal, PreOrderWithEnterAndLeave) {
    auto root = Directory::make_root();
    auto& a = root->emplace<Directory>("a");
    a.emplace<File>("x", 1);
    root->emplace<File>("b", 1);

    RecordingVisitor v;
    root->accept(v);
    EXPECT_EQ(v.events, (std::vector<std::string>{"enter /", "enter /a", "file x", "leave /a",
                                                  "file b", "leave /"}));
}

TEST(Traversal, ReturningFalseFromEnterPrunesSubtreeAndSkipsLeave) {
    auto root = Directory::make_root();
    auto& a = root->emplace<Directory>("a");
    a.emplace<File>("x", 1);

    RecordingVisitor v;
    v.skip = "/a";
    root->accept(v);
    EXPECT_EQ(v.events, (std::vector<std::string>{"enter /", "enter /a", "leave /"}));
}

// ---- TreePrinter -------------------------------------------------------------

TEST(TreePrinter, DrawsTreeWithConnectorsAndSizes) {
    const auto root = sample_tree();
    std::ostringstream out;
    TreePrinter printer(out);
    root->accept(printer);

    EXPECT_EQ(out.str(),
              "/ (2.4 KiB)\n"
              "├── Makefile (5 B)\n"
              "├── README.md (10 B)\n"
              "├── empty/ (0 B)\n"
              "└── src/ (2.4 KiB)\n"
              "    ├── core/ (2.3 KiB)\n"
              "    │   ├── node.cpp (2.0 KiB)\n"
              "    │   └── node.hpp (300 B)\n"
              "    └── main.cpp (100 B)\n");
}

TEST(TreePrinter, RespectsMaxDepthAndNoSizes) {
    const auto root = sample_tree();
    std::ostringstream out;
    TreePrinter printer(out, {.show_sizes = false, .max_depth = 1});
    root->accept(printer);

    EXPECT_EQ(out.str(),
              "/\n"
              "├── Makefile\n"
              "├── README.md\n"
              "├── empty/\n"
              "└── src/\n");
}

TEST(TreePrinter, CanStartFromASubtree) {
    const auto root = sample_tree();
    std::ostringstream out;
    TreePrinter printer(out, {.show_sizes = false});
    root->resolve("src/core")->accept(printer);

    EXPECT_EQ(out.str(),
              "/src/core\n"
              "├── node.cpp\n"
              "└── node.hpp\n");
}

TEST(TreePrinter, PrintsALoneFile) {
    const File f("solo.txt", 2048);
    std::ostringstream out;
    TreePrinter printer(out);
    f.accept(printer);
    EXPECT_EQ(out.str(), "solo.txt (2.0 KiB)\n");
}

// ---- FindVisitor -------------------------------------------------------------

TEST(Find, GlobMatchesFilesAndDirectories) {
    const auto root = sample_tree();
    EXPECT_EQ(paths(find(*root, match::name_glob("*.cpp"))),
              (std::vector<std::string>{"/src/core/node.cpp", "/src/main.cpp"}));
    EXPECT_EQ(paths(find(*root, match::name_glob("co*"))),
              (std::vector<std::string>{"/src/core"}));
}

TEST(Find, CombinedPredicates) {
    const auto root = sample_tree();
    const auto big_files = find(*root, match::all_of({match::files_only(), match::min_size(200)}));
    EXPECT_EQ(paths(big_files),
              (std::vector<std::string>{"/src/core/node.cpp", "/src/core/node.hpp"}));

    const auto dirs = find(*root, match::directories_only());
    EXPECT_EQ(paths(dirs), (std::vector<std::string>{"/", "/empty", "/src", "/src/core"}));
}

TEST(Find, EmptyAllOfMatchesEverything) {
    const auto root = sample_tree();
    EXPECT_EQ(find(*root, match::all_of({})).size(), 9u);
}

TEST(Find, NoMatchesYieldsEmptyResult) {
    const auto root = sample_tree();
    EXPECT_TRUE(find(*root, match::name_glob("*.rs")).empty());
}

// ---- StatsVisitor ------------------------------------------------------------

TEST(Stats, AggregatesInOnePass) {
    const auto root = sample_tree();
    StatsVisitor stats;
    root->accept(stats);

    EXPECT_EQ(stats.file_count(), 5u);
    EXPECT_EQ(stats.directory_count(), 4u);
    EXPECT_EQ(stats.total_bytes(), root->size());
    EXPECT_EQ(stats.max_depth(), 3u);
    ASSERT_NE(stats.largest_file(), nullptr);
    EXPECT_EQ(stats.largest_file()->name(), "node.cpp");

    const auto& ext = stats.by_extension();
    ASSERT_EQ(ext.size(), 4u);
    EXPECT_EQ(ext.at("cpp").files, 2u);
    EXPECT_EQ(ext.at("cpp").bytes, 2148u);
    EXPECT_EQ(ext.at("(none)").files, 1u);
}

TEST(Stats, EmptyTree) {
    const auto root = Directory::make_root();
    StatsVisitor stats;
    root->accept(stats);
    EXPECT_EQ(stats.file_count(), 0u);
    EXPECT_EQ(stats.directory_count(), 1u);
    EXPECT_EQ(stats.largest_file(), nullptr);
}

TEST(Stats, ReportListsExtensionsByBytes) {
    const auto root = sample_tree();
    StatsVisitor stats;
    root->accept(stats);
    std::ostringstream out;
    print_report(out, stats);

    const std::string text = out.str();
    EXPECT_NE(text.find("files:        5"), std::string::npos);
    EXPECT_NE(text.find("largest file: /src/core/node.cpp (2.0 KiB)"), std::string::npos);
    EXPECT_LT(text.find("cpp"), text.find("hpp"));  // larger bucket first
}
