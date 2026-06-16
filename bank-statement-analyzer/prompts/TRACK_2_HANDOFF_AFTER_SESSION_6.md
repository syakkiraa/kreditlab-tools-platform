# Track 2 handoff — picking up after session 6

State at end-of-session-6 (2026-05-02). Use this when starting a fresh
chat to continue Track 2 work. The current chat ran sessions 1-6 in one
sitting and is being paused for the human to run two follow-ups in a new
chat with cleaner context.

## Current state

**Branch:** `track-2-development` at commit `b6bbedd` (pushed to origin).

**What is done — six sessions, ten functions, 147 unit tests, all
passing:**

| Session | Commit | Function(s) | Feeds Flag(s) |
|---|---|---|---|
| 1 | `0398843` | `compute_monthly_eod` | (foundation for C22 / Flag 4) |
| 2 | `7d83a4f` | `compute_risk_flags` (the 16-flag reducer) + `CANONICAL_FLAGS` | terminal step for all 16 |
| 3 | `c75168b` | `compute_statutory_compliance` | 6, 7, 8, 16 |
| 4 | `2a72a85` | `compute_round_figure_credits` (C21), `compute_large_credits` (C23), `compute_high_value_credits` (C22) | 3, 4, 9 |
| 5 | `3b2eb8b` | `compute_returned_cheques` (C14/C15), `compute_data_completeness`, `compute_fx_totals` (+ `is_fx_transaction`) | 1, 2, 13, 14 |
| 6 | `b6bbedd` | `compute_monthly_aggregates` (per-month, bank-agnostic, Streamlit-free) | 15 |

All ten functions live in [kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py). All 147 tests live under [tests/](../tests/) and run via:

```bash
python -m unittest discover tests
```

**Flag coverage now: 12 of 16 lit by Track 2.** Still need classification
inputs for Flag 5 (cash deposits / C17), Flag 10 (own-party / C01-C02),
Flag 11 (related-party / C03-C04), Flag 12 (loan activity / C10-C11).

## Mid-flight state — DO NOT TOUCH

The working tree currently has unstaged modifications to two files from
**a separate workstream the user is running in another chat**:

- `app.py` — BUG-001 fix (per-bank `calculate_monthly_summary` totals
  switched from "trust footer" to "sum transactions")
- `core_utils.py` — BUG-003 fix (`normalize_company_suffix` for truncated
  SDN BHD tails)

**Rule for the next agent:** never `git add`, `git stash`, `git checkout`,
or otherwise touch these two files. Stage Track 2 work explicitly by
path (e.g. `git add kredit_lab_classify_track2.py tests/<file>`) so the
two unstaged files stay exactly where the user left them. This was a
real session-3 incident — auto-staging caused a 0.2pp Felcra rate drop
investigation panic. Don't repeat it.

Once the user lands BUG-001/BUG-003 in their other chat, the working
tree clears and Track 1 verify rates can be re-measured cleanly.

## Two open items the user wants to tackle next

### Item A — spot-check Track 2 against real data

Every test so far is synthetic hand-crafted rows. Goal: run the new
session-6 `compute_monthly_aggregates` over one real corpus and confirm
the math survives real parser output. **Felcra (Bank Rakyat folder 8)
is the smallest at 4,373 rows / 6 PDFs — start there.**

Suggested approach:

```python
import sys, glob, json
from pathlib import Path
sys.path.insert(0, ".")

import pdfplumber
from bank_rakyat import parse_bank_rakyat
from core_utils import normalize_transactions
from kredit_lab_classify_track2 import compute_monthly_aggregates

rows = []
for p in sorted(glob.glob("Bank-Statement/BankRakyat/8/*.pdf")):
    with pdfplumber.open(p) as pdf:
        parsed = parse_bank_rakyat(pdf)
    rows.extend(
        normalize_transactions(parsed, default_bank="Bank Rakyat", source_file=Path(p).name)
    )

# Optionally split by source_file or account_no — caller responsibility.
agg = compute_monthly_aggregates(rows, account_type="CR")
print(json.dumps(agg, indent=2))
```

**Compare against:**

- `validation_runs/track2_eod_baseline.txt` (committed in session 1) —
  Felcra was 6 months, eod_average range [35,530.61, 225,064.77]. The new
  `compute_monthly_aggregates` should produce the same eod_average per
  month as `compute_monthly_eod` did then, plus extra fields.
- One real PDF's footer totals (e.g. open one Bank Rakyat PDF and read
  the "Total Debit / Total Credit / Closing Balance" line) — confirm
  Track 2's `gross_credits` / `gross_debits` / `closing_balance` for that
  month match (within RM1 tolerance for rounding).
- `app.py:calculate_monthly_summary` output for the same corpus — but
  note the user's BUG-001 fix may not be merged yet; if not, the
  comparison will reveal exactly the discrepancy BUG-001 fixes.

If the comparison shows divergence, document it and decide whether it's
a Track 2 bug or a Track 1 quirk — don't auto-fix without checking.

**Time budget: ~30 minutes.** Worth doing before any session 7 work.

### Item B — decide where Track 2 classification stops

Sessions 1-6 ported reducers and rule-only computations (math, regex,
band thresholds). Sessions 7+ would shift to **classification logic**:
deciding which category each row gets. That changes the work shape —
classification has judgment calls that the architecture memo says belong
in the thin Track 2 AI prompt, not in code.

The four remaining unfilled flags need these classifications:

| Flag | Category | Difficulty | Notes |
|---|---|---|---|
| 5 | C17 cash deposit | Easy (keyword) | CDM, CASH DEPOSIT — bank-variant keywords |
| 10 | C01/C02 own-party | Medium | Needs `company_name` + name-match logic. Truncation handling is BUG-003 territory (your other chat). |
| 11 | C03/C04 related-party | **Hard** | Needs resolved RP list. Tier 3 algorithmic per architecture memo (RP2/RP3/RP5/RP6/RP7/RP8 detection rules). Memo says RP detection is one of the *judgment* items that may stay in the thin AI prompt. |
| 12 | C10/C11 loan disbursement / repayment | Medium-Hard | Account-number-only loans, vehicle plate detection (C11), known-factoring entity list (C10), C02+C11 dual-tag for company-named loans. Tier 3 per memo. |

**Decision the user owes the next session:** for each of these, "code it
in Track 2" vs "leave it for the Track 2 thin AI prompt." The
architecture memo's default suggests:

- C17 (cash deposit keywords) — code it. Pure keyword match like C14/C15.
- C18 (cash withdrawal) — code it. Same shape.
- C24 (bank fees keywords) — code it. Same shape.
- C19/C20 (cheque deposit/issue keywords) — code it. Same shape.
- C01/C02 (own-party) — code it (after BUG-003 lands so name truncation
  is normalized).
- **C05 salary** — split: simple keyword list in code, ambiguous
  commission-cluster handling stays in prompt.
- **C10 loan disbursement / C11 loan repayment** — split: account-number-only and known-factoring stays in code (deterministic); director-personal-loan vs company-loan distinction stays in prompt (needs resolved RP list).
- **C03/C04 related-party** — leave whole thing for prompt (RP detection
  is the judgment item explicitly called out in the architecture memo).

The user should confirm or override this split before session 7 starts.

## Architecture rules (re-read before any code)

- Track 1 files frozen indefinitely:
  - `kredit_lab_classify.py`
  - `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`
  - `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`
- Track 2 must not import from Track 1 classifier code, and vice versa.
- Parsers and `core_utils` are SHARED infrastructure (both tracks consume
  the same canonical row data). Improvements to either benefit both
  tracks — but Track 2 sessions don't *initiate* parser/core_utils
  edits unless the user explicitly approves.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.

## First commands the next session should run

```bash
git status --short                                    # confirm clean / known-dirty
git branch --show-current                             # MUST be track-2-development
git log --oneline -3                                  # confirm at b6bbedd or later
python -m unittest discover tests 2>&1 | tail -5      # confirm 147/147
```

Expected output of the last line:

```
Ran 147 tests in 0.00Xs
OK
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Out of scope for the next session

- Don't edit Track 1 files (see architecture rules).
- Don't touch `app.py` or `core_utils.py` while they show as modified
  in `git status` — those belong to the user's BUG-001/BUG-003 chat.
- Don't run all 6 verify scripts to chase rates while shared infra is
  dirty — output will conflate workstreams. Track 1 verify is owed but
  blocked on the other chat finishing first (this is fine; Track 2
  isolation is preserved at the import-graph level regardless).
- Don't run the Track 2 sanity script (`scripts/track2_eod_sanity.py`)
  unless you have time for the 6-corpus parse pass (~3-5 min).

## Memory entries that should already be loaded

The user's auto-memory should pull these on session start:

- `project_track_2_architecture.md` — the 2026-05-01 thin-AI decision
- `feedback_track_isolation_design.md` — Track 1 vs Track 2 file isolation
- `project_ship_ready_strategy.md` — engine 6-8 sessions away from sellable
- `feedback_no_sdk_until_bank_deploy.md` — file-based handoff to claude.ai for now

If any are missing or seem stale, refresh from the actual code — memory
records are point-in-time snapshots and the truth is in the repo.
