"""Regenerate the golden snapshot files for the Track 1 verify-harness
regression suite.

Run from the repo root::

    python scripts/regenerate_regression_snapshots.py            # all
    python scripts/regenerate_regression_snapshots.py mazaa_pbb  # one

Use this AFTER an intentional behavioural change (parser fix, rulebook
edit, classifier change) that you've validated produces the new numbers
you expect. Commit the refreshed snapshot JSONs in the same commit as
the underlying code change so the regression diff is meaningful.

The test runner (``tests/regression/test_snapshots.py``) compares the
live pipeline against these snapshots and fails on any drift.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests.regression._harness import (
    CORPORA,
    build_snapshot,
    snapshot_path,
)


def main() -> int:
    labels = [c["label"] for c in CORPORA]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "label",
        nargs="?",
        default="all",
        choices=labels + ["all"],
        help="snapshot label to regenerate (default: all)",
    )
    args = ap.parse_args()
    targets = labels if args.label == "all" else [args.label]
    specs = {c["label"]: c for c in CORPORA}

    for label in targets:
        spec = specs[label]
        print(f"==> regenerating {label}", flush=True)
        snap = build_snapshot(spec)
        out = snapshot_path(label)
        out.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n")
        print(
            f"    wrote {out.relative_to(REPO_ROOT)} "
            f"(parsed={snap['parsed_rows']}, classified="
            f"{snap['classification']['classified']}/{snap['classification']['total']}"
            f" = {snap['classification']['rate_pct']:.1f}%)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
