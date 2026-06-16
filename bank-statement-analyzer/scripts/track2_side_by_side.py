"""Side-by-side validation harness — Track 1 vs Track 2 on the same corpus.

Loads a parser-produced ``full_report.json``, drives BOTH classifiers
headlessly, and emits a structured diff covering top-level keys, section
counts, aggregate amounts, and category-bin overlaps.

This is the MVP gate per Track 2 architecture memo: when this harness shows
Track 2 within tolerance of Track 1 across the 6-corpus baseline (modulo
the deliberate v3.5.6 divergences), Track 2 ships.

Run from repo root::

    python scripts/track2_side_by_side.py <full_report.json>
    python scripts/track2_side_by_side.py <full_report.json> --out /tmp/diff
    python scripts/track2_side_by_side.py <full_report.json> --full

The ``--out`` flag dumps both raw outputs + the machine-readable diff to a
directory for offline inspection. ``--full`` prints per-line observation
text alongside the count summary.

Track 1 is driven with default ``AnalystDecisions`` (no analyst inputs) so
the comparison is reproducible. RP3/RP4 confirmations would alter Track 1's
C03/C04 counts; running with defaults isolates the deterministic floor.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import kredit_lab_classify as t1
import kredit_lab_classify_track2 as t2


# ── Track 1 headless driver ────────────────────────────────────────────────


def run_track1(data: dict[str, Any]) -> dict[str, Any]:
    """Mirror ``streamlit_main`` without the Streamlit / analyst form.

    Auto-RP Step 1 parity: the production Streamlit path runs
    ``scan_related_party_candidates`` and merges HIGH-confidence names
    into ``AnalystDecisions.related_parties`` before classification.
    Track 2's ``build_track2_result`` does the same inside the
    orchestrator, so the harness must auto-confirm here too — otherwise
    Track 1 reports 0 RP fires while Track 2 reports the full
    auto-confirmed set and the diff is meaningless."""
    account_meta = t1.detect_account_type(data)
    recon = t1.reconcile_balance_trail(data, account_meta["convention"])
    rulebook = t1.load_rulebook()
    rp_candidates = t1.scan_related_party_candidates(data)
    auto_rp = t1.auto_confirmed_related_parties(rp_candidates)
    decisions = t1.AnalystDecisions(related_parties=list(auto_rp))

    classified = t1.classify_transactions(data, rulebook, decisions)
    monthly = t1.build_monthly_analysis(classified, data, recon)
    consolidated = t1.build_consolidated(monthly)
    top_parties = t1.build_top_parties(classified, decisions.related_parties)
    large_credits = t1.build_large_credits(classified)
    own_related = t1.build_own_related_transactions(classified)
    loans = t1.build_loan_transactions(classified)
    unclassified = t1.build_unclassified(classified)
    flags = t1.build_flags(consolidated, monthly)
    observations = t1.build_observations(consolidated, flags)
    parsing_metadata = t1.build_parsing_metadata(data, recon)

    return t1.assemble_analysis_json(
        data=data,
        classified=classified,
        monthly=monthly,
        consolidated=consolidated,
        top_parties=top_parties,
        large_credits=large_credits,
        own_related=own_related,
        loans=loans,
        flags=flags,
        observations=observations,
        unclassified=unclassified,
        parsing_metadata=parsing_metadata,
        account_meta=account_meta,
    )


# ── Track 2 headless driver ────────────────────────────────────────────────


def run_track2(data: dict[str, Any]) -> dict[str, Any]:
    """Single-call orchestrator. account_meta intentionally omitted — Track 2
    treats every account as Current/non-OD by default, which matches Track 1
    when no OD limit is provided.

    ``summary.company_names`` is threaded in so the dispatcher's non-marker
    C01/C02 own-party rung (RP foundation Slice 1) can fire on corpora
    whose parser output didn't carry the ``(OWN-PARTY)`` stamp."""
    summary = data.get("summary") or {}
    company_names = summary.get("company_names") or []
    return t2.build_track2_result(
        data.get("transactions") or [],
        counterparty_ledger=data.get("counterparty_ledger"),
        pdf_integrity=data.get("pdf_integrity"),
        company_names=list(company_names),
    )


# ── Diff helpers ───────────────────────────────────────────────────────────


def _sum(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(float(r.get(key) or 0.0) for r in rows), 2)


def _section_diff_monthly(
    t1_monthly: list[dict[str, Any]],
    t2_monthly: list[dict[str, Any]],
) -> dict[str, Any]:
    fields = ("gross_credits", "gross_debits", "net_credits", "net_debits")
    return {
        "count": {"t1": len(t1_monthly), "t2": len(t2_monthly),
                  "delta": len(t2_monthly) - len(t1_monthly)},
        **{
            f: {"t1": _sum(t1_monthly, f), "t2": _sum(t2_monthly, f),
                "delta": round(_sum(t2_monthly, f) - _sum(t1_monthly, f), 2)}
            for f in fields
        },
    }


def _section_diff_consolidated(
    t1_cons: dict[str, Any],
    t2_cons: dict[str, Any],
) -> dict[str, Any]:
    """Compare consolidated scalars. Nested dict / list fields collapse to a
    boolean equality + key-set summary (full payload lives in --out dumps)."""
    keys = sorted(set(t1_cons) | set(t2_cons))
    out: dict[str, Any] = {}
    for k in keys:
        v1, v2 = t1_cons.get(k), t2_cons.get(k)
        if isinstance(v1, dict) or isinstance(v2, dict):
            d1 = v1 if isinstance(v1, dict) else {}
            d2 = v2 if isinstance(v2, dict) else {}
            out[k] = {
                "kind": "dict",
                "equal": v1 == v2,
                "t1_keys": sorted(d1),
                "t2_keys": sorted(d2),
                "t2_only_keys": sorted(set(d2) - set(d1)),
                "t1_only_keys": sorted(set(d1) - set(d2)),
            }
        elif isinstance(v1, list) or isinstance(v2, list):
            l1 = v1 if isinstance(v1, list) else []
            l2 = v2 if isinstance(v2, list) else []
            out[k] = {
                "kind": "list",
                "equal": v1 == v2,
                "t1_len": len(l1),
                "t2_len": len(l2),
            }
        elif isinstance(v1, (int, float)) or isinstance(v2, (int, float)):
            v1f = float(v1 or 0.0)
            v2f = float(v2 or 0.0)
            out[k] = {"kind": "scalar", "t1": round(v1f, 2),
                      "t2": round(v2f, 2),
                      "delta": round(v2f - v1f, 2)}
        else:
            out[k] = {"kind": "other", "t1": v1, "t2": v2,
                      "equal": v1 == v2}
    return out


def _section_diff_top_parties(
    t1_tp: dict[str, Any],
    t2_tp: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for side in ("top_credit_parties", "top_debit_parties"):
        l1 = t1_tp.get(side) or []
        l2 = t2_tp.get(side) or []
        n1 = {p.get("party_name") for p in l1}
        n2 = {p.get("party_name") for p in l2}
        out[side] = {
            "t1_count": len(l1),
            "t2_count": len(l2),
            "shared": len(n1 & n2),
            "t1_only": sorted(n1 - n2),
            "t2_only": sorted(n2 - n1),
        }
    return out


def _section_diff_flags(
    t1_flags: dict[str, Any] | list[dict[str, Any]],
    t2_flags: dict[str, Any],
) -> dict[str, Any]:
    # Track 1 wraps as {"indicators": [...]}; Track 2 same shape per orchestrator.
    t1_ind = (
        t1_flags.get("indicators") if isinstance(t1_flags, dict) else t1_flags
    ) or []
    t2_ind = (t2_flags.get("indicators") or []) if isinstance(t2_flags, dict) else []

    def _by_id(ind: list[dict[str, Any]]) -> dict[str, bool]:
        return {str(i.get("indicator_id") or i.get("name") or ""):
                bool(i.get("detected")) for i in ind}

    a, b = _by_id(t1_ind), _by_id(t2_ind)
    diffs = sorted(k for k in (set(a) | set(b))
                   if a.get(k) != b.get(k))
    return {
        "t1_count": len(t1_ind),
        "t2_count": len(t2_ind),
        "detected_t1": sum(1 for v in a.values() if v),
        "detected_t2": sum(1 for v in b.values() if v),
        "verdict_diffs": diffs,
    }


def _section_diff_own_related(
    t1_or: dict[str, Any], t2_or: dict[str, Any]
) -> dict[str, Any]:
    t1_tx = (t1_or or {}).get("transactions") or []
    t2_tx = (t2_or or {}).get("transactions") or []
    return {
        "count": {"t1": len(t1_tx), "t2": len(t2_tx),
                  "delta": len(t2_tx) - len(t1_tx)},
        "amount": {
            "t1": _sum(t1_tx, "amount"),
            "t2": _sum(t2_tx, "amount"),
            "delta": round(_sum(t2_tx, "amount") - _sum(t1_tx, "amount"), 2),
        },
    }


def _section_diff_loans(
    t1_l: dict[str, Any], t2_l: dict[str, Any]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in ("disbursements", "repayments"):
        l1 = (t1_l or {}).get(k) or []
        l2 = (t2_l or {}).get(k) or []
        out[k] = {
            "count": {"t1": len(l1), "t2": len(l2), "delta": len(l2) - len(l1)},
            "amount": {
                "t1": _sum(l1, "amount"),
                "t2": _sum(l2, "amount"),
                "delta": round(_sum(l2, "amount") - _sum(l1, "amount"), 2),
            },
        }
    return out


def _section_diff_observations(
    t1_obs: dict[str, Any], t2_obs: dict[str, Any]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in ("positive", "concerns"):
        l1 = (t1_obs or {}).get(k) or []
        l2 = (t2_obs or {}).get(k) or []
        out[k] = {
            "t1_count": len(l1),
            "t2_count": len(l2),
            "t1_lines": l1,
            "t2_lines": l2,
        }
    return out


def build_diff(t1_out: dict[str, Any], t2_out: dict[str, Any]) -> dict[str, Any]:
    keys_t1 = set(t1_out)
    keys_t2 = set(t2_out)

    diff: dict[str, Any] = {
        "top_level_keys": {
            "shared": sorted(keys_t1 & keys_t2),
            "t1_only": sorted(keys_t1 - keys_t2),
            "t2_only": sorted(keys_t2 - keys_t1),
        },
        "accounts_count": {
            "t1": len(t1_out.get("accounts") or []),
            "t2": len(t2_out.get("accounts") or []),
        },
        "monthly_analysis": _section_diff_monthly(
            t1_out.get("monthly_analysis") or [],
            t2_out.get("monthly_analysis") or [],
        ),
        "consolidated": _section_diff_consolidated(
            t1_out.get("consolidated") or {},
            t2_out.get("consolidated") or {},
        ),
        "top_parties": _section_diff_top_parties(
            t1_out.get("top_parties") or {},
            t2_out.get("top_parties") or {},
        ),
        "large_credits_count": {
            "t1": len(t1_out.get("large_credits") or []),
            "t2": len(t2_out.get("large_credits") or []),
        },
        "own_related_transactions": _section_diff_own_related(
            t1_out.get("own_related_transactions") or {},
            t2_out.get("own_related_transactions") or {},
        ),
        "loan_transactions": _section_diff_loans(
            t1_out.get("loan_transactions") or {},
            t2_out.get("loan_transactions") or {},
        ),
        "flags": _section_diff_flags(
            t1_out.get("flags") or {}, t2_out.get("flags") or {},
        ),
        "observations": _section_diff_observations(
            t1_out.get("observations") or {},
            t2_out.get("observations") or {},
        ),
        "unclassified_count": {
            "t1": len(t1_out.get("unclassified_transactions") or []),
            "t2": len(t2_out.get("unclassified_transactions") or []),
        },
    }
    return diff


# ── Pretty-printer ─────────────────────────────────────────────────────────


def _money(v: Any) -> str:
    try:
        return f"RM {float(v):>16,.2f}"
    except (TypeError, ValueError):
        return f"{v!s:>20}"


def print_summary(diff: dict[str, Any], *, full: bool = False) -> None:
    p = print

    p("=" * 78)
    p("Side-by-side: Track 1 (kredit_lab_classify) vs Track 2 (build_track2_result)")
    p("=" * 78)

    tl = diff["top_level_keys"]
    p(f"\nTop-level keys — shared {len(tl['shared'])}, "
      f"t1-only {len(tl['t1_only'])}, t2-only {len(tl['t2_only'])}")
    if tl["t1_only"]:
        p(f"  t1-only: {tl['t1_only']}")
    if tl["t2_only"]:
        p(f"  t2-only: {tl['t2_only']}")

    p(f"\nAccounts — t1={diff['accounts_count']['t1']}  "
      f"t2={diff['accounts_count']['t2']}")

    m = diff["monthly_analysis"]
    p(f"\nmonthly_analysis — count t1={m['count']['t1']}  "
      f"t2={m['count']['t2']}  Δ={m['count']['delta']:+d}")
    for f in ("gross_credits", "gross_debits", "net_credits", "net_debits"):
        d = m[f]
        marker = "" if abs(d["delta"]) < 0.01 else "  ⚠"
        p(f"    {f:<14} t1={_money(d['t1'])}  t2={_money(d['t2'])}  "
          f"Δ={_money(d['delta'])}{marker}")

    p("\nconsolidated — fields where t1 and t2 disagree:")
    cons = diff["consolidated"]
    any_div = False
    for k, v in sorted(cons.items()):
        kind = v.get("kind")
        if kind == "scalar" and abs(v["delta"]) >= 0.01:
            any_div = True
            p(f"    {k:<26} t1={_money(v['t1'])}  t2={_money(v['t2'])}  "
              f"Δ={_money(v['delta'])}")
        elif kind == "dict" and not v["equal"]:
            any_div = True
            extra = []
            if v["t2_only_keys"]:
                extra.append(f"t2-only:{v['t2_only_keys']}")
            if v["t1_only_keys"]:
                extra.append(f"t1-only:{v['t1_only_keys']}")
            note = "  " + " ".join(extra) if extra else ""
            p(f"    {k:<26} ⚠ nested dict differs{note}")
        elif kind == "list" and not v["equal"]:
            any_div = True
            p(f"    {k:<26} ⚠ list differs (t1_len={v['t1_len']}  t2_len={v['t2_len']})")
        elif kind == "other" and not v["equal"]:
            any_div = True
            p(f"    {k:<26} t1={v['t1']!r}  t2={v['t2']!r}  ⚠ unequal")
    if not any_div:
        p("    (all consolidated fields match)")

    tp = diff["top_parties"]
    for side in ("top_credit_parties", "top_debit_parties"):
        s = tp[side]
        p(f"\n{side} — t1={s['t1_count']}  t2={s['t2_count']}  "
          f"shared={s['shared']}")
        if s["t1_only"]:
            p(f"    t1 only: {s['t1_only'][:5]}{'...' if len(s['t1_only']) > 5 else ''}")
        if s["t2_only"]:
            p(f"    t2 only: {s['t2_only'][:5]}{'...' if len(s['t2_only']) > 5 else ''}")

    p(f"\nlarge_credits — t1={diff['large_credits_count']['t1']}  "
      f"t2={diff['large_credits_count']['t2']}")

    o = diff["own_related_transactions"]
    p(f"\nown_related_transactions — count t1={o['count']['t1']}  "
      f"t2={o['count']['t2']}  Δ={o['count']['delta']:+d}  "
      f"amount Δ={_money(o['amount']['delta'])}")

    lt = diff["loan_transactions"]
    for k in ("disbursements", "repayments"):
        s = lt[k]
        p(f"\nloan_transactions.{k} — count t1={s['count']['t1']}  "
          f"t2={s['count']['t2']}  Δ={s['count']['delta']:+d}  "
          f"amount Δ={_money(s['amount']['delta'])}")

    f = diff["flags"]
    p(f"\nflags.indicators — t1={f['t1_count']} ({f['detected_t1']} detected)  "
      f"t2={f['t2_count']} ({f['detected_t2']} detected)")
    if f["verdict_diffs"]:
        p(f"    verdict mismatches on indicator_ids: {f['verdict_diffs']}")
    else:
        p("    all indicator detect-verdicts match")

    obs = diff["observations"]
    for k in ("positive", "concerns"):
        s = obs[k]
        p(f"\nobservations.{k} — t1={s['t1_count']}  t2={s['t2_count']}")
        if full:
            for line in s["t1_lines"]:
                p(f"    [t1] {line}")
            for line in s["t2_lines"]:
                p(f"    [t2] {line}")

    p(f"\nunclassified_transactions — t1={diff['unclassified_count']['t1']}  "
      f"t2={diff['unclassified_count']['t2']}")

    p("\n" + "=" * 78)


# ── CLI ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("full_report", type=Path,
                        help="Path to a parser-produced full_report.json")
    parser.add_argument("--out", type=Path, default=None,
                        help="Optional dir to write track1.json / track2.json / diff.json")
    parser.add_argument("--full", action="store_true",
                        help="Also print per-line observation text")
    args = parser.parse_args()

    if not args.full_report.exists():
        parser.error(f"file not found: {args.full_report}")

    data = json.loads(args.full_report.read_text())

    print(f"Loaded {args.full_report.name}: "
          f"{len(data.get('transactions') or [])} transactions, "
          f"{len(data.get('monthly_summary') or [])} monthly summary rows")

    t1_out = run_track1(data)
    t2_out = run_track2(data)
    diff = build_diff(t1_out, t2_out)

    print_summary(diff, full=args.full)

    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "track1.json").write_text(json.dumps(t1_out, indent=2, default=str))
        (args.out / "track2.json").write_text(json.dumps(t2_out, indent=2, default=str))
        (args.out / "diff.json").write_text(json.dumps(diff, indent=2, default=str))
        print(f"Wrote raw outputs + diff.json to {args.out}/")


if __name__ == "__main__":
    main()
