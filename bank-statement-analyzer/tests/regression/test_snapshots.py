"""Golden-snapshot regression tests for the 6 Track 1 verify harnesses.

Compares the live pipeline output against the JSON snapshots under
``tests/regression/snapshots/`` and fails on any drift. Snapshots are
regenerated via::

    python scripts/regenerate_regression_snapshots.py

The suite is SKIPPED BY DEFAULT (parses ~35 real PDFs, ~75s wall) and
only runs when ``RUN_REGRESSION=1`` is set in the environment. The
default ``python -m unittest discover tests`` invocation stays fast.

To run::

    RUN_REGRESSION=1 python -m unittest tests.regression.test_snapshots -v
"""

from __future__ import annotations

import json
import logging
import os
import unittest
from pathlib import Path

# Suppress Streamlit's "missing ScriptRunContext" warnings — they fire
# because ``app.py`` is a Streamlit module and we import its utility
# functions outside a Streamlit run.
logging.getLogger("streamlit").setLevel(logging.ERROR)

from tests.regression._harness import (
    CORPORA,
    build_snapshot,
    snapshot_path,
)


SHOULD_RUN = os.environ.get("RUN_REGRESSION") == "1"


@unittest.skipUnless(
    SHOULD_RUN,
    "regression suite is opt-in (parses ~35 PDFs, ~75s); set RUN_REGRESSION=1 to enable",
)
class RegressionSnapshotTests(unittest.TestCase):
    """One test method per corpus — generated dynamically below."""

    maxDiff = None


def _make_test(spec: dict):
    label = spec["label"]
    golden_path: Path = snapshot_path(label)

    def test(self: unittest.TestCase) -> None:
        self.assertTrue(
            golden_path.exists(),
            f"golden snapshot missing: {golden_path}. "
            f"Run `python scripts/regenerate_regression_snapshots.py {label}` first.",
        )
        golden = json.loads(golden_path.read_text())
        live = build_snapshot(spec)
        self.assertEqual(
            golden,
            live,
            f"\n\nSnapshot drift on {label!r}.\n"
            f"If this is an intentional change, regenerate via:\n"
            f"    python scripts/regenerate_regression_snapshots.py {label}\n"
            f"and commit the updated JSON.\n",
        )

    test.__name__ = f"test_{label}"
    test.__doc__ = f"Snapshot regression: {label}"
    return test


for _spec in CORPORA:
    setattr(RegressionSnapshotTests, f"test_{_spec['label']}", _make_test(_spec))


if __name__ == "__main__":
    unittest.main()
