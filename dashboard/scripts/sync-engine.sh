#!/usr/bin/env bash
#
# sync-engine.sh — pull the Financial Statement Analyzer engine from the
# standalone repo (the source of truth) into this dashboard.
#
# The dashboard runs its OWN copy of the analysis engine under
# financial-statement-analysis-logic/. The standalone repo is where you
# develop + parity-test the engine; this script copies the latest engine
# files in so the dashboard stays in sync.
#
# Usage:
#   ./scripts/sync-engine.sh           # show drift, then copy updated files
#   ./scripts/sync-engine.sh --check   # dry run: only report what differs
#
# Override the source location if you ever move the standalone repo:
#   KL_ENGINE_SOURCE="/path/to/repo" ./scripts/sync-engine.sh
#
set -euo pipefail

SOURCE="${KL_ENGINE_SOURCE:-/Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Financial Statement Analyzer HTML (Renderer)/repo}"
DEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/financial-statement-analysis-logic"

# Files the dashboard depends on. render_bridge.py is dashboard-only and is
# intentionally NOT synced (it's the glue, not part of the engine).
FILES=(
  "analyze.py"
  "KreditLab_v7_9_6.txt"
  "streamlit_financial_report_v7_7.py"
  "excel_export.py"
)

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

if [ ! -d "$SOURCE" ]; then
  echo "❌ Standalone engine repo not found at:"
  echo "   $SOURCE"
  echo "   Set KL_ENGINE_SOURCE to the correct path and retry."
  exit 1
fi

echo "Source: $SOURCE"
echo "Dest:   $DEST_DIR"
echo

changed=0
missing=0
for f in "${FILES[@]}"; do
  src="$SOURCE/$f"
  dst="$DEST_DIR/$f"

  if [ ! -f "$src" ]; then
    echo "⚠️  source missing: $f  (skipped)"
    missing=$((missing + 1))
    continue
  fi

  if [ -f "$dst" ] && diff -q "$src" "$dst" >/dev/null 2>&1; then
    echo "✓  up to date:   $f"
    continue
  fi

  changed=$((changed + 1))
  if [ "$CHECK_ONLY" = "1" ]; then
    echo "≠  WOULD UPDATE: $f"
  else
    cp "$src" "$dst"
    echo "⬇️  synced:       $f"
  fi
done

echo
if [ "$CHECK_ONLY" = "1" ]; then
  echo "Dry run: $changed file(s) differ, $missing missing. No files copied."
else
  echo "Done: $changed file(s) updated, $missing missing."
  if [ "$changed" -gt 0 ]; then
    echo "Tip: review with 'git -C \"$(dirname "$DEST_DIR")\" diff -- financial-statement-analysis-logic'"
    echo "     No dev-server restart needed — the engine is spawned fresh each analysis."
  fi
fi
