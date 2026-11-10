#!/usr/bin/env python3
"""Check that each `compile_fail,EXXXX` doctest in src/machine.rs fails with
exactly the error code it claims.

Stable rustdoc only checks that a `compile_fail` block fails to compile, not
*why*. A typo could make a block fail for the wrong reason and the doctest
would still pass. This script compiles each block as a temporary example and
compares the reported error codes.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOCK = re.compile(r"//! ```compile_fail,(E\d{4})\n(.*?)//! ```\n", re.S)


def to_program(body: str) -> str:
    lines = [re.sub(r"^//! ?(# )?", "", line) for line in body.splitlines()]
    if any(line.startswith(("struct ", "impl ")) for line in lines):
        return "\n".join(lines) + "\nfn main() {}\n"  # item-level snippet
    return "fn main() {\n" + "\n".join(lines) + "\n}\n"


def main() -> int:
    source = (ROOT / "src" / "machine.rs").read_text()
    blocks = BLOCK.findall(source)
    if not blocks:
        print("no compile_fail blocks found")
        return 1
    examples = ROOT / "examples"
    failures = 0
    for i, (expected, body) in enumerate(blocks):
        name = f"_compile_fail_{i}"
        path = examples / f"{name}.rs"
        path.write_text(to_program(body))
        try:
            result = subprocess.run(
                ["cargo", "build", "-q", "--example", name],
                cwd=ROOT, capture_output=True, text=True,
            )
        finally:
            path.unlink()
        codes = set(re.findall(r"error\[(E\d{4})\]", result.stderr))
        ok = codes == {expected}
        failures += not ok
        print(f"block {i}: expected {expected}, got {sorted(codes) or 'success'} {'ok' if ok else 'MISMATCH'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
