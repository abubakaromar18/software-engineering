#include <iostream>
#include <string_view>
#include <vector>

#include "vfs/cli.hpp"

int main(int argc, char* argv[]) {
    const std::vector<std::string_view> args(argv + 1, argv + argc);
    return vfs::cli::run(args, std::cin, std::cout, std::cerr);
}
