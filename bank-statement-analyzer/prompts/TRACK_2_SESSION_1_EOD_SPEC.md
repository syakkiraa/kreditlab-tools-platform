# Track 2 — Session 1 spec: EOD computation migration

**Goal:** create `kredit_lab_classify_track2.py` and port the EOD (End-of-Day balance) computation algorithm from the v3.5.6 AI prompt into deterministic Python code. This is the first Tier-2 migration — chosen because it's a pure, well-defined algorithm with no business judgment, ~30-50 LOC, and establishes the foundation file for all subsequent Track 2 work.

## Context for the session

- **Branch:** `track-2-development` (already created at commit `39fa68a`, same point as `sprint-6/polish`).
- **Track 1 files MUST NOT be touched.** `kredit_lab_classify.py`, `SYSTEM_PROMPT_v3_5_6.md`, `CLASSIFICATION_RULES_v3_5.json` are frozen. See `~/.claude/.../memory/project_track_2_architecture.md` for the architecture rules.
- **Source spec for EOD:** `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md` lines 558-583. That section defines the exact algorithm. Track 2 implements it in code.

## Algorithm (verbatim from the prompt, lines 562-583)

```
1. Walk transactions in statement order — the order they appear in the
   extracted data (matching PDF order), NOT sorted by amount or description.
2. Group by date — for each unique transaction date in the month, collect
   all transactions.
3. EOD balance for each date = the running balance on the LAST transaction
   of that date (the balance column value of the final transaction row for
   that day).
4. Collect all daily EOD balances into a list for the month.

Monthly EOD metrics:
   eod_lowest  = MIN(all daily EOD balances in the month)
   eod_highest = MAX(all daily EOD balances in the month)
   eod_average = SUM(all daily EOD balances) / COUNT(distinct dates with transactions)

Rules:
- Only dates with transactions count — weekends/holidays with no activity
  are NOT included (do not carry forward the previous day's balance to fill gaps).
- Opening balance date: if the opening-balance row has a date AND no other
  transactions on that date, the opening balance IS the EOD for that date.
  If other transactions exist on the same date, use the last transaction's
  balance instead.
- Opening balance from previous month: if the opening-balance date belongs
  to the PREVIOUS month (e.g. 30-Sep opening for an Oct statement), do NOT
  include it in the current month's EOD calculation.
- Closing balance is implicit — it equals the EOD of the last transaction
  date in the month. Do not double-count.
```

## File and function design

### File location

```
kredit_lab_classify_track2.py    ← NEW file at repo root
```

The file does not exist yet. The first session creates it. Top-of-file docstring should declare:

> Track 2 deterministic classifier — engine-heavy migration of v3.5.6 AI-prompt
> classification logic. Companion file to `kredit_lab_classify.py` (Track 1,
> frozen). See `~/.claude/.../memory/project_track_2_architecture.md` for the
> migration plan and `prompts/NEXT_CHAT_PROMPT.md` for session handoffs.

### Function signature

```python
def compute_monthly_eod(
    transactions: list[dict[str, Any]],
    year_month: str,
) -> dict[str, float | int | None]:
    """Compute end-of-day balance metrics for a single account-month.

    Args:
        transactions: list of transaction dicts in canonical schema, already
            sorted by source-file order (statement order). Must contain only
            rows for ONE account; caller is responsible for per-account
            grouping. Each row has at minimum: 'date' (ISO YYYY-MM-DD),
            'balance' (float | None).
        year_month: target month in 'YYYY-MM' format. Only transactions
            whose 'date' starts with this prefix are included.

    Returns:
        dict with keys:
            'eod_lowest': float — MIN of daily EOD balances
            'eod_highest': float — MAX of daily EOD balances
            'eod_average': float — SUM / COUNT of daily EOD balances
            'eod_dates_count': int — number of distinct dates with transactions
        If the month has no transactions, returns the dict with all values None
        (caller decides how to render).
    """
```

### Implementation outline (do not pre-write — the session writes it fresh)

1. Filter `transactions` to rows whose `date.startswith(year_month)`. Skip rows where `balance is None`.
2. Group filtered rows by date (preserving statement order within each date group).
3. For each date, take the LAST row's `balance` as that date's EOD.
4. Compute min, max, sum, count from the daily-EOD list.
5. Handle empty case (no transactions in month) — return None for each metric.

The opening-balance and previous-month handling rules from the algorithm spec apply at the **caller** level (the orchestrator decides which rows to pass in). The function itself just trusts its input. Document this assumption in the docstring.

## Validation methodology

The deterministic engine currently does NOT compute EOD — that work lives only in the AI prompt today. So there's no Track 1 Python output to compare against directly. Validation has three layers:

### Layer 1 — Algorithm conformance (unit tests)

Write unit tests with hand-crafted inputs where the answer is known. Cover at minimum:

| Test case | Input shape | Expected output |
|---|---|---|
| Single date, single transaction | 1 row, balance=1000.00, date=2026-04-15 | low=high=avg=1000, count=1 |
| Single date, multiple transactions | 3 rows on 2026-04-15, balances 500, 800, 1200 | low=high=avg=1200 (last balance), count=1 |
| Multiple dates, distinct EODs | 3 rows on 3 different dates, EODs 100, 200, 300 | low=100, high=300, avg=200, count=3 |
| Empty month | 0 rows | all metrics None, count=0 |
| Mixed: month boundary | rows from 2026-04 and 2026-05 with year_month='2026-04' | only April rows counted |
| Balance is None | rows with some balance=None | None-balance rows skipped |
| Statement-order matters | 3 rows on same date, balances arrive in order [800, 200, 500] | last is 500, not min(200) |

Test file: `tests/test_track2_eod.py` (create the `tests/` directory if it doesn't exist).

### Layer 2 — Cross-corpus sanity check (read-only)

Run the EOD function over each of the 6 verify corpora and produce a summary:

```
Felcra:        N months, eod_average range [X, Y]
Mazaa:         N months, eod_average range [X, Y]
Waja:          N months, eod_average range [X, Y]
Mytutor:       N months, eod_average range [X, Y]
KMZ:           N months, eod_average range [X, Y]
PrincipalGas:  N months, eod_average range [X, Y]
```

Sanity check: values should be plausible (positive for CR accounts, negative for OD accounts, reasonable orders of magnitude). Spot-check 1-2 values against statement headers to confirm.

### Layer 3 — Track 1 parity check (deferred, optional for session 1)

Once Track 2 has more functions, the full Track 2 classifier output can be compared against Track 1's AI output on the same input. Don't try to do this in session 1 — too much surface area, too little Track 2 code. EOD's Layer 1 + Layer 2 is sufficient for now.

## Acceptance criteria for session 1

Before declaring EOD migration done:

1. ✅ `kredit_lab_classify_track2.py` exists at repo root with module docstring.
2. ✅ `compute_monthly_eod()` function implemented per spec above.
3. ✅ All 7 unit tests in `tests/test_track2_eod.py` pass.
4. ✅ Layer 2 cross-corpus sanity output produced and committed as `validation_runs/track2_eod_baseline.txt` (or similar — exact path to be decided).
5. ✅ Track 1 verify scripts STILL pass with unchanged rates:
   - `verify_felcra_v3a.py` → 59.2%
   - `verify_mazaa_v3a.py` → 92.2%
   - `verify_waja_v3a.py` → 25.5%
   - `verify_bimb_v3a.py mytutor` → 1.3%
   - `verify_bimb_v3a.py kmz` → 39.6%
   - `verify_bimb_v3a.py principal_gas` → 30.7%
   This proves Track 2 work didn't accidentally bleed into Track 1.
6. ✅ Commit on `track-2-development` branch with clear message: `Track 2 session 1: EOD computation port (Tier 2)`.
7. ✅ Push `track-2-development` to remote so future sessions have continuity.

## What NOT to do in session 1

- ❌ Don't edit `kredit_lab_classify.py` (Track 1 frozen).
- ❌ Don't edit `SYSTEM_PROMPT_v3_5_6.md` or `CLASSIFICATION_RULES_v3_5.json`.
- ❌ Don't try to migrate any other Tier 2 item in the same session — keep scope tight.
- ❌ Don't import from `kredit_lab_classify` (Track 1 → Track 2 import is forbidden).
- ❌ Don't add the runtime switch to `app.py` yet (that's session 9 territory).
- ❌ Don't try to compare Track 2 output against Track 1 AI output yet (deferred to validation phase).

## First commands the session should run

```bash
git status --short                                # confirm clean tree
git branch --show-current                         # MUST be track-2-development
git log --oneline -3                              # confirm at 39fa68a or later

# Verify Track 1 baseline before any Track 2 work:
python scripts/verify_felcra_v3a.py | grep "CLASSIFICATION RATE"     # 59.2%
python scripts/verify_mazaa_v3a.py | grep "CLASSIFICATION RATE"      # 92.2%
python scripts/verify_waja_v3a.py | grep "CLASSIFICATION RATE"       # 25.5%
python scripts/verify_bimb_v3a.py mytutor | grep "CLASSIFICATION"    # 1.3%
python scripts/verify_bimb_v3a.py kmz | grep "CLASSIFICATION"        # 39.6%
python scripts/verify_bimb_v3a.py principal_gas | grep "CLASSIFICATION" # 30.7%
```

If any of these don't match, STOP — something on the branch has drifted. Re-verify the branch state before any Track 2 code.

## Why EOD first (vs other Tier 2 candidates)

The handoff also suggested 16-flag computation as a possible session-1 target. EOD wins because:

- **Smaller scope** (~30-50 LOC vs ~200 for 16-flag computation, which depends on many summary fields).
- **Self-contained** — depends only on `transactions` list with `date` and `balance` fields. No coupling to other Track 2 functions yet.
- **Testable in isolation** — Layer 1 unit tests don't need any classification work to validate.
- **Foundation pattern** — establishes the file structure, import conventions, test layout that subsequent migrations follow.

After EOD ships, session 2 can pick up 16-flag computation OR another small Tier 2 item with the foundation already in place.
