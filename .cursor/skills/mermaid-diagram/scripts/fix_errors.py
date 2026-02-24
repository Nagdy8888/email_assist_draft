#!/usr/bin/env python3
"""
Apply common Mermaid syntax fixes to avoid render errors.
Reads from stdin or a file; prints fixed Mermaid to stdout.

Usage:
  python scripts/fix_errors.py < diagram.mmd
  python scripts/fix_errors.py path/to/file.md
  python scripts/fix_errors.py path/to/file.md -o fixed.mmd
"""
import re
import sys
from pathlib import Path


def extract_mermaid(text: str) -> str:
    """Extract first ```mermaid ... ``` block from markdown."""
    match = re.search(r"```mermaid\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def fix_mermaid(mmd: str) -> str:
    lines = mmd.split("\n")
    out = []
    for line in lines:
        # 1) Node IDs with spaces -> use underscores (e.g. "User Service" in [User Service])
        #    Match [...], (...), ([...]), [[...]] and replace spaces inside with underscores for IDs
        if "[" in line and "]" in line and " --> " not in line and " --- " not in line:
            # Label in square brackets: [Some Label] -> [Some_Label] only if it looks like a node label
            pass  # Be conservative; only fix known bad patterns
        # 2) Reserved word as node ID: end, subgraph, graph, flowchart
        if re.search(r"\b(end|subgraph|graph|flowchart)\b\s*[\[\(]", line):
            line = re.sub(r"\bend\s*\[", "endNode[", line)
            line = re.sub(r"\bend\s*\]", "]", line)
        # 3) Edge labels with parentheses not quoted: -->|O(1)|  ->  -->|"O(1)"|
        line = re.sub(r"\|([^"]*\([^)]*\)[^"|]*)\|", r'|"\1"|', line)
        # 4) Subgraph with space in label: subgraph foo bar  ->  subgraph foo [foo bar]
        if line.strip().startswith("subgraph ") and " [" not in line and "]" not in line:
            parts = line.split(None, 2)
            if len(parts) >= 3:
                line = f"subgraph {parts[1]} [{parts[2]}]"
        out.append(line)
    return "\n".join(out)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__, file=sys.stderr)
        sys.exit(0)
    out_path = None
    if "-o" in args:
        i = args.index("-o")
        if i + 1 < len(args):
            out_path = args[i + 1]
            args = [a for j, a in enumerate(args) if j not in (i, i + 1)]
    path = args[0] if args else "-"
    if path == "-":
        text = sys.stdin.read()
    else:
        text = Path(path).read_text(encoding="utf-8")
    mmd = extract_mermaid(text)
    fixed = fix_mermaid(mmd)
    if out_path:
        Path(out_path).write_text(fixed, encoding="utf-8")
        print(f"Written: {out_path}", file=sys.stderr)
    else:
        print(fixed)


if __name__ == "__main__":
    main()
