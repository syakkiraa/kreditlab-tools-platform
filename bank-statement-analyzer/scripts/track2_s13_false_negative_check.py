"""Session 13 false-negative spot-check.

Run every corpus file in the April 2026 pre-parser-fix baseline through
the s12-calibrated statutory chain. Output a verdict table so we can
verify that the SUB_THRESHOLD / CHANNEL_BLIND branches don't downgrade
*real* CRITICAL gaps to softer verdicts (false negatives).

Compare against the s11 expected breakdown (the 5 named CRITICAL accounts
should now be COMPLIANT/SUB_THRESHOLD/CHANNEL_BLIND per the s12 handoff).
For the other ~15 salary-detected files we just want to make sure
nothing that should be CRITICAL has silently slipped down.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kredit_lab_classify_track2 import (
    compute_salary_payments,
    compute_epf_payments,
    compute_socso_payments,
    compute_lhdn_tax_payments,
    compute_hrdf_payments,
    compute_statutory_monthly_amounts,
    compute_statutory_compliance,
)

CORPUS = (
    ROOT
    / "validation runs - json"
    / "claude ai prompt file"
    / "Full Report Sample (April 2026 - pre-parser-fix baseline)"
)


def run_one(path: Path) -> dict:
    raw = json.loads(path.read_text())
    transactions = raw.get("transactions") or []

    salary = compute_salary_payments(transactions)
    epf = compute_epf_payments(transactions)
    socso = compute_socso_payments(transactions)
    lhdn = compute_lhdn_tax_payments(transactions)
    hrdf = compute_hrdf_payments(transactions)

    monthly = compute_statutory_monthly_amounts(
        salary_entries=salary["salary_payments_entries"],
        epf_entries=epf["epf_payments_entries"],
        socso_entries=socso["socso_payments_entries"],
        lhdn_tax_entries=lhdn["lhdn_tax_payments_entries"],
        hrdf_entries=hrdf["hrdf_payments_entries"],
    )

    stat = compute_statutory_compliance(monthly, transactions=transactions)

    return {
        "file": path.name,
        "tx_count": len(transactions),
        "salary_count": salary["salary_payments_count"],
        "salary_total_rm": salary["salary_payments_amount"],
        "salary_months": stat["salary_months_active"],
        "epf_pct": stat["epf_coverage_pct"],
        "socso_pct": stat["socso_coverage_pct"],
        "overall": stat["overall_status"],
        "subthreshold": stat["subthreshold_employer"]["is_subthreshold"],
        "channel_blind": stat["channel_blind_employer"]["is_channel_blind"],
        "cheque_dr_rm": stat["channel_blind_employer"].get("cheque_dr_amount", 0.0),
        "cheque_dr_ratio": stat["channel_blind_employer"].get("cheque_dr_ratio", 0.0),
    }


def main() -> None:
    files = sorted(p for p in CORPUS.glob("*.json") if ".classified" not in p.name)
    rows = [run_one(p) for p in files]

    salary_active = [r for r in rows if r["salary_months"] > 0]
    salary_dormant = [r for r in rows if r["salary_months"] == 0]

    print(f"Files scanned: {len(rows)}")
    print(f"Salary-detected (≥1 active month): {len(salary_active)}")
    print(f"No-salary files: {len(salary_dormant)}")
    print()

    if salary_active:
        header = (
            f"{'File':<55} {'Tx':>5} {'SalCnt':>7} {'SalRM':>14}"
            f" {'Mo':>3} {'EPF%':>6} {'SOC%':>6} {'Verdict':<14}"
            f" {'SubT':>5} {'ChBl':>5} {'ChqRM':>14} {'ChqR':>5}"
        )
        print(header)
        print("-" * len(header))
        for r in sorted(
            salary_active,
            key=lambda x: (x["overall"], -x["salary_total_rm"]),
        ):
            short = r["file"][:55]
            print(
                f"{short:<55} {r['tx_count']:>5} {r['salary_count']:>7}"
                f" {r['salary_total_rm']:>14,.2f}"
                f" {r['salary_months']:>3} {r['epf_pct']:>6.1f}"
                f" {r['socso_pct']:>6.1f} {r['overall']:<14}"
                f" {str(r['subthreshold'])[0]:>5} {str(r['channel_blind'])[0]:>5}"
                f" {r['cheque_dr_rm']:>14,.0f} {r['cheque_dr_ratio']:>5.2f}"
            )

    print()
    # Verdict distribution.
    from collections import Counter
    dist = Counter(r["overall"] for r in salary_active)
    print("Verdict distribution (salary-active only):", dict(dist))


if __name__ == "__main__":
    main()
