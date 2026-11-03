#include "vfs/cli.hpp"

#include <charconv>
#include <fstream>
#include <vector>

#include "vfs/manifest.hpp"
#include "vfs/node.hpp"
#include "vfs/text.hpp"
#include "vfs/visitors.hpp"

namespace vfs::cli {

namespace {

std::uint64_t parse_number(std::string_view flag, std::string_view value) {
    std::uint64_t n = 0;
    const auto* end = value.data() + value.size();
    const auto [ptr, ec] = std::from_chars(value.data(), end, n);
    if (value.empty() || ec != std::errc{} || ptr != end) {
        throw UsageError(std::string{flag} + " expects a non-negative integer, got '" +
                         std::string{value} + "'");
    }
    return n;
}

const Node& resolve_start(const Directory& root, std::string_view start) {
    const Node* node = root.resolve(start);
    if (node == nullptr) {
        throw std::runtime_error("no such path: " + std::string{start});
    }
    return *node;
}

void print_matches(std::ostream& out, const std::vector<const Node*>& matches, bool sizes) {
    for (const Node* n : matches) {
        out << n->path() << (n->is_directory() && n->parent() ? "/" : "");
        if (sizes) out << "  " << human_size(n->size());
        out << '\n';
    }
}

}  // namespace

std::string usage() {
    return "usage: vfs-tree [options] <manifest | ->\n"
           "\n"
           "Prints a virtual filesystem described by a manifest file.\n"
           "\n"
           "options:\n"
           "  --at PATH         operate on the subtree at PATH (default /)\n"
           "  --find GLOB       list entries whose name matches GLOB (* and ?)\n"
           "  --min-size BYTES  with --find: only entries at least this large\n"
           "  --files           with --find: only files\n"
           "  --stats           print counts, sizes and an extension histogram\n"
           "  --depth N         limit tree expansion to N levels (0 = unlimited)\n"
           "  --no-sizes        omit sizes from output\n"
           "  -h, --help        show this help\n";
}

Options parse_args(std::span<const std::string_view> args) {
    Options opts;
    bool have_manifest = false;

    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string_view arg = args[i];
        auto value = [&]() -> std::string_view {
            if (i + 1 >= args.size()) throw UsageError(std::string{arg} + " requires a value");
            return args[++i];
        };

        if (arg == "-h" || arg == "--help") {
            opts.help = true;
        } else if (arg == "--at") {
            opts.start = value();
        } else if (arg == "--find") {
            opts.find_glob = std::string{value()};
        } else if (arg == "--min-size") {
            opts.min_size = parse_number(arg, value());
        } else if (arg == "--files") {
            opts.files_only = true;
        } else if (arg == "--stats") {
            opts.stats = true;
        } else if (arg == "--depth") {
            opts.max_depth = static_cast<std::size_t>(parse_number(arg, value()));
        } else if (arg == "--no-sizes") {
            opts.show_sizes = false;
        } else if (arg.starts_with("-") && arg != "-") {
            throw UsageError("unknown option: " + std::string{arg});
        } else if (have_manifest) {
            throw UsageError("unexpected argument: " + std::string{arg});
        } else {
            opts.manifest_path = arg;
            have_manifest = true;
        }
    }
    if (!opts.help && !have_manifest) {
        throw UsageError("missing manifest path");
    }
    if (!opts.find_glob && (opts.min_size != 0 || opts.files_only)) {
        throw UsageError("--min-size and --files require --find");
    }
    return opts;
}

int run(std::span<const std::string_view> args, std::istream& stdin_stream, std::ostream& out,
        std::ostream& err) {
    Options opts;
    try {
        opts = parse_args(args);
    } catch (const UsageError& e) {
        err << "error: " << e.what() << "\n\n" << usage();
        return 2;
    }
    if (opts.help) {
        out << usage();
        return 0;
    }

    try {
        std::unique_ptr<Directory> root;
        if (opts.manifest_path == "-") {
            root = parse_manifest(stdin_stream);
        } else {
            std::ifstream file(opts.manifest_path);
            if (!file) throw std::runtime_error("cannot open " + opts.manifest_path);
            root = parse_manifest(file);
        }
        const Node& start = resolve_start(*root, opts.start);

        if (opts.find_glob) {
            std::vector<Predicate> preds{match::name_glob(*opts.find_glob)};
            if (opts.min_size != 0) preds.push_back(match::min_size(opts.min_size));
            if (opts.files_only) preds.push_back(match::files_only());
            print_matches(out, find(start, match::all_of(std::move(preds))), opts.show_sizes);
        } else if (opts.stats) {
            StatsVisitor stats;
            start.accept(stats);
            print_report(out, stats);
        } else {
            TreePrinter printer(out, {.show_sizes = opts.show_sizes, .max_depth = opts.max_depth});
            start.accept(printer);
        }
        return 0;
    } catch (const std::exception& e) {
        err << "error: " << e.what() << '\n';
        return 1;
    }
}

}  // namespace vfs::cli
