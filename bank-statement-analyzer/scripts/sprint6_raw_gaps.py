"""Sprint 6 raw-method extraction-gap enumerator.

For every Full Report JSON in the corpus, re-runs `build_counterparty_ledger`
to get the CURRENT extraction state (reflecting the code on the live branch,
not the extraction_method stamp baked into the stored ledger). Collects every
tx where extraction_method == "raw" and groups them by (bank, first-3-token-
shape) so the largest extraction gaps surface first.

Usage:
    python3 scripts/sprint6_raw_gaps.py                # top-5 shapes per bank
    python3 scripts/sprint6_raw_gaps.py --bank AMBANK  # all shapes, one bank
    python3 scripts/sprint6_raw_gaps.py --shape 'CIB IBG CA'
    python3 scripts/sprint6_raw_gaps.py --out /tmp/raw_gaps.json
    python3 scripts/sprint6_raw_gaps.py --samples 10 --top 10

Run this before picking an extraction handler to build and after shipping each
handler to confirm rows moved out of raw. Diff = progress.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import pathlib
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Silence streamlit bare-mode warnings that fire on `import app`.
logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

with contextlib.redirect_stderr(io.StringIO()):
    import app as app_mod  # noqa: E402

CORPUS_DIR = ROOT / "validation runs - json" / "claude ai prompt file" / "Full Report Sample"

NUM_RE = re.compile(r"-?\d[\d,.]*")
DATE_RE = re.compile(r"\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?")
CARD_RE = re.compile(r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}")


def shape(desc: str, n_tokens: int = 3) -> str:
    """Normalise the first n tokens so similar descriptions collapse into one bucket."""
    toks = (desc or "").split()[:n_tokens]
    out = []
    for t in toks:
        if CARD_RE.fullmatch(t):
            out.append("CARD")
        elif DATE_RE.fullmatch(t):
            out.append("DATE")
        elif NUM_RE.fullmatch(t):
            out.append("NUM")
        else:
            out.append(t.upper()[:24])
    return " ".join(out) or "(empty)"


def load_corpus_files() -> List[pathlib.Path]:
    return sorted(
        p for p in CORPUS_DIR.glob("Full Report *.json")
        if not p.name.endswith(".classified.json")
    )


def enumerate_gaps(samples_per_shape: int = 3, n_tokens: int = 3) -> Dict[str, Any]:
    per_bank_shape: Dict[str, Counter] = defaultdict(Counter)
    per_bank_shape_samples: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    per_bank_shape_files: Dict[Tuple[str, str], Counter] = defaultdict(Counter)

    for p in load_corpus_files():
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            print(f"  skip {p.name}: {e}", file=sys.stderr)
            continue
        txs = data.get("transactions") or []
        ledger = app_mod.build_counterparty_ledger(txs)
        for cp in ledger.get("counterparties") or []:
            cp_name = cp.get("counterparty_name") or ""
            for tx in cp.get("transactions") or []:
                if tx.get("extraction_method") != "raw":
                    continue
                bank = (tx.get("bank") or "").upper()
                desc = tx.get("description") or ""
                sh = shape(desc, n_tokens=n_tokens)
                per_bank_shape[bank][sh] += 1
                per_bank_shape_files[(bank, sh)][p.name] += 1
                lst = per_bank_shape_samples[(bank, sh)]
                if len(lst) < samples_per_shape:
                    lst.append({
                        "file": p.name,
                        "desc": desc,
                        "cp_name": cp_name,
                        "debit": tx.get("debit") or tx.get("amount") if tx.get("type") == "debit" else None,
                        "credit": tx.get("credit") or tx.get("amount") if tx.get("type") == "credit" else None,
                    })
    return {
        "per_bank_shape": {b: dict(c) for b, c in per_bank_shape.items()},
        "per_bank_shape_samples": {f"{b}|||{s}": v for (b, s), v in per_bank_shape_samples.items()},
        "per_bank_shape_files": {f"{b}|||{s}": dict(c) for (b, s), c in per_bank_shape_files.items()},
    }


def print_report(data: Dict[str, Any], top_shapes: int = 5, bank_filter: str | None = None,
                 shape_filter: str | None = None, samples_shown: int = 3) -> None:
    per_bank_shape = {b: Counter(c) for b, c in data["per_bank_shape"].items()}
    samples_map = data["per_bank_shape_samples"]
    files_map = data["per_bank_shape_files"]

    bank_totals = sorted(
        ((b, sum(c.values())) for b, c in per_bank_shape.items()),
        key=lambda kv: -kv[1],
    )
    if bank_filter:
        bank_totals = [(b, t) for b, t in bank_totals if bank_filter.upper() in b]

    grand = sum(t for _, t in bank_totals)
    print("=" * 100)
    print(f"raw-method extraction gaps  (total rows: {grand}, banks: {len(bank_totals)})")
    print("=" * 100)

    for bank, total in bank_totals:
        print(f"\n--- {bank}  (total raw: {total}) ---")
        shapes = per_bank_shape[bank].most_common()
        if shape_filter:
            shapes = [(s, c) for s, c in shapes if shape_filter.upper() in s]
        if not bank_filter and not shape_filter:
            shapes = shapes[:top_shapes]
        for sh, cnt in shapes:
            files_hit = Counter(files_map.get(f"{bank}|||{sh}", {}))
            files_summary = ", ".join(f"{n}×{c}" for n, c in files_hit.most_common(3))
            print(f"  {cnt:5d}  shape={sh!r}")
            print(f"         in files: {files_summary}")
            for s in samples_map.get(f"{bank}|||{sh}", [])[:samples_shown]:
                desc = s.get("desc", "")
                print(f"         e.g. {desc[:140]!r}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", help="Filter to one bank (substring match on tx.bank, case-insensitive)")
    ap.add_argument("--shape", help="Filter to shapes containing this substring (uppercased)")
    ap.add_argument("--top", type=int, default=5, help="Top-N shapes per bank (ignored with --bank/--shape)")
    ap.add_argument("--samples", type=int, default=3, help="Sample descriptions to print per shape")
    ap.add_argument("--tokens", type=int, default=3, help="Tokens used for shape key (default 3)")
    ap.add_argument("--out", type=pathlib.Path, help="Also dump raw gap data to this JSON")
    args = ap.parse_args()

    data = enumerate_gaps(samples_per_shape=max(args.samples, 3), n_tokens=args.tokens)
    print_report(
        data,
        top_shapes=args.top,
        bank_filter=args.bank,
        shape_filter=args.shape,
        samples_shown=args.samples,
    )
    if args.out:
        args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"\n[OK] full gap data written -> {args.out}")


if __name__ == "__main__":
    main()
