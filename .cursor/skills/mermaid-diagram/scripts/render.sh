#!/usr/bin/env bash
# Render Mermaid diagram to SVG/PNG. Uses npx so no global install needed.
# Usage:
#   ./scripts/render.sh path/to/file.md [output.svg]
#   ./scripts/render.sh path/to/diagram.mmd [output.svg]
#   echo "flowchart LR; A-->B" | ./scripts/render.sh - output.svg
# Requires: Node.js (npx), Puppeteer (installed by mermaid-cli)

set -e
INPUT="${1:?Usage: render.sh <input.md|input.mmd|-> [output.svg]]}"
OUTPUT="${2:-output.svg}"
TEMP_MMD=$(mktemp).mmd

cleanup() { rm -f "$TEMP_MMD"; }
trap cleanup EXIT

extract_mermaid() {
  local file="$1"
  if [[ "$file" == "-" ]]; then
    cat
  elif grep -q '```mermaid' "$file" 2>/dev/null; then
    sed -n '/^```mermaid$/,/^```$/p' "$file" | sed '1d;$d'
  else
    cat "$file"
  fi
}

extract_mermaid "$INPUT" > "$TEMP_MMD"
npx --yes @mermaid-js/mermaid-cli@latest -i "$TEMP_MMD" -o "$OUTPUT" -b transparent
echo "Rendered: $OUTPUT"
