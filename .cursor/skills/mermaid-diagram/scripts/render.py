#!/usr/bin/env python3
"""
Render Mermaid diagram to SVG (or PNG). Uses npx @mermaid-js/mermaid-cli (mmdc).
Requires: Node.js (npx). Works on Windows and Unix.

Usage:
  python scripts/render.py path/to/file.md [output.svg]
  python scripts/render.py path/to/diagram.mmd
  python scripts/render.py -o diagram.svg path/to/file.md
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_mermaid(text: str) -> str:
    """Extract first ```mermaid ... ``` block from markdown."""
    match = re.search(r"```mermaid\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def main():
    args = sys.argv[1:]
    if "-o" in args:
        idx = args.index("-o")
        output = args[idx + 1]
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
    else:
        output = args[1] if len(args) >= 2 else "output.svg"
    if not args or args[0] in ("-h", "--help"):
        print(__doc__, file=sys.stderr)
        sys.exit(0)
    input_spec = args[0]
    if input_spec == "-":
        mmd = sys.stdin.read()
    else:
        text = Path(input_spec).read_text(encoding="utf-8")
        mmd = extract_mermaid(text)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".mmd", delete=False, encoding="utf-8"
    ) as f:
        f.write(mmd)
        tmp = f.name
    try:
        subprocess.run(
            ["npx", "--yes", "@mermaid-js/mermaid-cli@latest", "-i", tmp, "-o", output, "-b", "transparent"],
            check=True,
        )
        print(f"Rendered: {output}", file=sys.stderr)
    finally:
        Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
