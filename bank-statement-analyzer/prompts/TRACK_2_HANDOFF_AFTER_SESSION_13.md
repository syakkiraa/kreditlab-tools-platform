# Track 2 handoff — picking up after session 13

State at end-of-session-13 (2026-05-13). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `154d953`. Two Track 2
commits in session 13 since the previous handoff (`58bd456`).

**Test count:** 687 / 687 (was 639 at session 12 end; +48 across one
commit, all session 13). Run `python -m unittest discover tests` to
verify.

**Two Track 2 commits added since the s13 handoff:**

| Commit | Function(s) / file | Tests | Role |
|---|---|---|---|
| `3890f98` | `scripts/track2_s13_false_negative_check.py` | — | Reusable corpus sweep verifying s12 calibration is FN-clean (s13) |
| `154d953` | `dispatch_transaction`; `classify_transactions`; `CANONICAL_CATEGORIES`; `DISPATCHER_BLOCKED_CATEGORIES`; `_is_balance_row`; `_BALANCE_ROW_RE` | 48 | Per-row dispatcher Slice A — unblocked rungs (s13) |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); new
tests in `tests/test_track2_dispatcher.py` (10 new classes).

## What session 13 unblocked

**The dispatcher Slice A is in.** `dispatch_transaction(row, **context)`
applies the v3.5 `global_rules.classification_order` priority ladder
for the UNBLOCKED rungs:

```
C25 balance row
  -> [C01/C02 own-party BLOCKED]
C05 salary  (uses is_salary_payment with s12 own-account guard)
  -> [C03/C04 RP BLOCKED]
C06/C07/C08/C09 statutory  (DR side, JomPAY-biller-only short-circuit)
  -> [C10/C11/C12 loan/FD BLOCKED]
C13 reversal credit  (CR side)
C14 returned cheque inward  (DR side, RETURNED_CHEQUE_RE)
C15 returned cheque outward (CR side)
C16 inward return  (CR side)
C17 cash deposit  (CR)
C18 cash withdrawal  (DR, "CASH CHQ DR" token)
C19 cheque deposit  (CR)
C20 cheque issue  (DR)
C24 bank fees  (DR)
C26 trade income / C27 trade expense
  (requires counterparty_name kwarg + has_corporate_suffix +
   not has_natural_person_marker)
-> None  (unclassified, stays in net credits/debits per v3.5
            no_unknown_bucket)
```

Blocked rungs accept forward-compat kwargs (`company_names`,
`related_parties`, `factoring_entities`) but do not fire. Those rungs
wait on the RP foundation sprint and BUG-003 (`normalize_company_suffix`
in `core_utils`).

`classify_transactions(transactions, *, counterparty_lookup, ...)`
orchestrates per-row dispatch and accepts an `index -> counterparty
name` lookup. When supplied, the C26/C27 rung fires; when omitted, those
rungs simply do not match and rows fall through to unclassified.

**Slice A corpus sanity-run (2026-05-13):**

| File | tx | classified | Top categories |
|---|---|---|---|
| Maybank Hydrise | 1013 | 28.5% | C20 168, C24 59, C07 22, C05 12, C06 6, C16 4, C09 7, C08 8, C13 2, C17 1 |
| Maybank Zaim | 2688 | 1.6% | C05 16, C24 10, C06 6, C07 4, C17 3, C08 2, C16 1 |
| MBB Shahnaz Builders | 181 | 13.3% | C20 13, C05 5, C24 3, C06 1, C08 1, C16 1 |

Low classification rates are EXPECTED. The blocked rungs (C01/C02
own-party, C03/C04 RP, C10/C11 loan, C26/C27 trade without counterparty
wiring) will catch the bulk of real transactions; until they land,
most rows pass through to "unclassified" and per v3.5
`no_unknown_bucket` stay in net credits/debits.

## What session 13 also verified

**s12 calibration is false-negative-clean** — handoff-suggested option 3
spot-check completed. Two drill-downs:

| Account | Verdict | Spot-check finding |
|---|---|---|
| Maybank Zaim | GAPS_DETECTED | Real APS payroll RM 56-82K/mo; FN scan confirmed no missed KWSP/PERKESO rows in the "missing" months — genuine partial coverage, not detector misses |
| Maybank Hydrise | COMPLIANT | Real RM 170-330K/mo payroll; EPF=25-26% and SOCSO=2% of salary monthly (correct regulatory rates); channel-blind T but inert because coverage is 100% |

Plus margin verification on the surviving CRITICALs:

- MBB Shahnaz Builders: cheque ratio 7.6% — 2.4pp below the 10%
  CHANNEL_BLIND threshold, BUT cheque magnitude RM 120K — RM 380K
  below the RM 500K floor. The **AND-gate** (both must clear)
  protects Shahnaz from a false-negative downgrade. This is now
  documented in memory.
- CIMB Naara: 0 cheque-DR + RM 95K salary (3.2× sub-threshold floor) —
  CRITICAL by huge margin.

Reproduce with `python scripts/track2_s13_false_negative_check.py`.

## Critical findings / decisions from session 13

### Dispatcher priority follows v3.5 classification_order verbatim

```python
CANONICAL_CATEGORIES = (
    "C25", "C01", "C02", "C05", "C03", "C04",
    "C06", "C07", "C08", "C09",
    "C10", "C11", "C12",
    "C13", "C14", "C15", "C16",
    "C17", "C18", "C19", "C20",
    "C24", "C26", "C27",
)
```

Note this differs from Track 1's `classify_transactions` which has
C01/C02 BEFORE C05 (bucket-direct path). Track 2 follows the v3.5
classification_order spec literally: C25 → [C01/C02] → C05 →
[C03/C04] → C06-C09 → [C10-C12] → C13-C20 → C24 → [C26/C27].
**C21-C23 are monitoring overlays applied after classification**, not
in the dispatcher.

### JomPAY guard is essentially a no-op for FULL_CODE C06-C09

Per the v3.5 `jompay_rule`, biller-code-only rows should not be
classified as C06-C09 / C11. The s8 `is_jompay_biller_code_only`
predicate is called before the C06-C09 keyword checks. **However**:
the predicate treats any alphabetic token of length ≥ 2 outside the
JOMPAY stopword set as "entity visible" — meaning "JOMPAY EPF" returns
False (entity-visible) and C06 fires anyway.

In practice the guard only suppresses "JOMPAY 12345" (just biller code,
no keyword) — but those rows wouldn't match any C06-C09 regex either,
so the suppression code path is dead weight in Slice A. Kept in place
because:
- Matches the section comment intent
- Costs ~one predicate call per DR row
- Becomes load-bearing if the s8 predicate is enhanced later (or if
  AI scoring fills in true biller-code-to-entity lookups)

If a future session tightens this, also tighten the s8 predicate's
stopword list to include statutory keywords like EPF / KWSP / SOCSO /
PERKESO / LHDN / HRDF — that's the right place, not the dispatcher.

### Returned-cheque regex uses CHQ abbreviation only

`RETURNED_CHEQUE_RE = (?:RETURN(?:ED)?\s+CHQ|CHQ\s+RETURN|DISHONOUR)`.
The spelled-out "CHEQUE" form does NOT match. The dispatcher Slice A
tests had to be updated to use "CHQ" abbreviation. If a future bank
parser emits "RETURNED CHEQUE" spelled out, the regex needs widening
on the Track 2 side (deliberate v3.5 divergence) OR the parser should
normalise. Flag if it bites.

### Bank fees regex is bank-token-anchored, not generic "service charge"

`BANK_FEES_RE` matches specific tokens: `MAS SERVICE CHARGE`,
`SERVICE TAX \d+%`, `STAMP DUTY`, `AUTOPAY CHARGES`, etc. Plain
"SERVICE CHARGE" does NOT match — it requires the `MAS` prefix or one
of the other listed tokens. This is the v3.5 LOCKED list, preserved
verbatim. If a parser starts emitting unprefixed `SERVICE CHARGE`
rows, extend the v3.5 keyword list (cross-track decision) rather than
adding a Track-2-only widening.

### Cash withdrawal regex is one literal: "CASH CHQ DR"

`CASH_WITHDRAWAL_RE = CASH\s+CHQ\s+DR`. Just one shape. If banks emit
"CASH WITHDRAWAL", "ATM CASH OUT", "COUNTER WITHDRAWAL" etc., they
will not match Track 2's C18 rung — they fall through to unclassified.
Same advice as above: extend the v3.5 keyword list if it bites.

### Counterparty extraction is the next chokepoint for Slice B

C26/C27 only fire when the caller passes `counterparty_name` via
`counterparty_lookup`. The corpus full_report JSONs carry
`counterparty_ledger` separately (Track 1 builds it via
`build_counterparty_ledger`), but Track 2 doesn't yet have a wiring
that joins ledger entries to transaction rows. Slice B's first move
should be: build `_build_counterparty_lookup_track2(transactions,
ledger)` returning `dict[int, str]` keyed on row enumeration index,
then pass it through to `classify_transactions`.

This is a "shared infrastructure" question (the ledger is built
upstream of the fork point), but the Track 2 dispatcher specifically
needs an index-keyed view of the join.

### Parallel-session branch flip — happened a 7th time

Mid-session-13 a parser-fix session ran `git stash && git checkout
parser-fix-mbb-rollover-rhb-monthly`. The Track 2 file disappeared from
disk mid-session. User chose to pause Track 2; parallel session
completed; branch returned to `track-2-development` and Track 2 work
resumed.

Durable mitigation (`git worktree add ../Bank-Statement-Track2
track-2-development`) declined **seven times now**. Treating as a
known cost — see `project_track_2_branch_drift.md` memory.

### Auto-merge feedback recorded mid-session

User added `feedback_auto_merge_solo.md` mid-session: ship verified fix
branches by direct merge to main + sync derivative, don't ask about PR
flow. Applies to fix-branch shipping (which is what triggered the
parallel session), NOT to substantive merges with conflicts. The
session-13 attempt to sync `main` into `track-2-development` surfaced a
real `app.py` conflict — user chose to defer the sync (calibration /
spot-check / dispatcher work doesn't depend on those parser fixes
beyond what's already cherry-picked into `track-2-development`).

## Sync state vs main

`track-2-development` is **16 commits behind main** as of end-of-s13.
Most of those commits are cherry-pick duplicates of fixes already on
`track-2-development` (51c2a1d ≈ f9d1377, e135511 ≈ d558e4e, etc.) —
the merge would have one substantive conflict in `app.py`. Deferred
pending a dedicated sync session. Track 2 work continues on the
diverged base because the classifier code is independent of the parser
fixes; the next session SHOULD NOT attempt the merge as part of normal
Track 2 work.

## Cumulative state across sessions 1-13

**Functions ported / built (37 total):**

- s1: `compute_monthly_eod`.
- s2: `compute_risk_flags` + `CANONICAL_FLAGS`.
- s3: `compute_statutory_compliance` (calibrated through s12, validated
  FN-clean in s13).
- s4: `compute_round_figure_credits` / `compute_large_credits` /
  `compute_high_value_credits`.
- s5: `compute_returned_cheques` / `compute_data_completeness` /
  `compute_fx_totals` + `is_fx_transaction`.
- s6: `compute_monthly_aggregates`.
- s7: `compute_cash_deposits` (C17), `compute_cash_withdrawals` (C18),
  `compute_cheque_deposits` (C19), `compute_cheque_issues` (C20),
  `compute_bank_fees` (C24), `compute_reversal_credits` (C13),
  `compute_inward_returns` (C16), `compute_net_totals`.
- s8: `validate_track2_result`, `is_jompay_biller_code_only`,
  `is_ghost_counterparty` + `filter_ghost_counterparties`,
  `has_corporate_suffix` + `has_natural_person_marker`,
  `canonicalise_counterparty_name` +
  `canonicalise_counterparty_entries`.
- s9: `pair_ibg_duitnow_returns` + helpers.
- s10: `compute_epf_payments` / `compute_socso_payments` /
  `compute_lhdn_tax_payments` / `compute_hrdf_payments` (C06-C09);
  `compute_statutory_monthly_amounts` (aggregator);
  `compute_unkeyworded_return_pair_count` + new
  `unkeyworded_return_pair_count` kwarg on `compute_data_completeness`.
- s11: `SALARY_KEYWORD_RE`, `COMMISSION_BLOCK_RE`,
  `is_salary_payment`, `compute_salary_payments` (C05).
- s12: `OWN_ACCOUNT_BLOCK_RE`; `SUBTHRESHOLD_TOTAL_SALARY_RM` +
  `is_subthreshold_employer`; `CHANNEL_BLIND_CHEQUE_DR_MIN_RM` +
  `CHANNEL_BLIND_CHEQUE_DR_MIN_RATIO` + `CHEQUE_DR_HEURISTIC_RE` +
  `compute_channel_blind_indicator`; `transactions=` kwarg +
  `SUB_THRESHOLD` / `CHANNEL_BLIND` overall_status branches on
  `compute_statutory_compliance`; `subthreshold_employer` +
  `channel_blind_employer` indicators on output; Flag 6/7 latent 0%
  fallback bug fix and remark-routing for both indicators.
- **NEW in s13:** `dispatch_transaction(row, **context)`;
  `classify_transactions(transactions, *, counterparty_lookup, ...)`;
  `CANONICAL_CATEGORIES` (v3.5 classification_order tuple);
  `DISPATCHER_BLOCKED_CATEGORIES` (frozenset of C01/C02/C03/C04/C10/
  C11/C12); `_is_balance_row` + `_BALANCE_ROW_RE` (C25 marker /
  description fallback).

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree carries uncommitted modifications
and untracked items from **other workstreams**:

- `scripts/sprint6_impact.py`, `scripts/sprint6_raw_gaps.py`,
  `scripts/validate_keywords.py` — modified ~2026-05-07. Unrelated.
  Preserved in `stash@{0}` if the parallel session stashed them again.
- Untracked directories under `Bank-Statement/`, `audit_reports/`,
  `bank-statement-analysis-HTML-fresh/`, `validation runs - json/...`,
  plus untracked prompt docs and the verify script
  `scripts/verify_ab_nov.py`.

**Rule:** stage Track 2 work explicitly by path (e.g.
`git add kredit_lab_classify_track2.py tests/<file>`). Never
`git add -A` / `git add .` / `git stash`.

## Big-picture progress

Per the 2026-05-01 architecture memo
([project_track_2_architecture.md](../validation%20runs%20-%20json/claude%20ai%20prompt%20file/SYSTEM_PROMPT_v3_5_6.md)
— see actual memo in user's auto-memory), original estimate was 8-12
sessions to working end-to-end Track 2. We are **13 sessions in**,
past the low estimate / at the high estimate. The s12 calibration
trio and s13 dispatcher are scope ADDITIONS not anticipated by the
original sequencing.

**Remaining to MVP Track 2 (passes side-by-side on 6 corpora):**

| Slice | Sessions | Gates |
|---|---|---|
| Dispatcher Slice B+C (counterparty wiring + orchestrator producing v6.3.5 result dict) | 1-2 | — |
| RP foundation sprint (RP3 scanner + RP6 constants, then RP2/5/7/8) | 2-3 | Unblocks C01-C04, C10, C11, factoring, M7 |
| Tier 3 remainder (C10 known-factoring, C11 priority logic, C11 account-number-only) | 1 | After RP foundation |
| `SYSTEM_PROMPT_TRACK2_v0_1.md` draft (Tier 4 prompt) | 1 | After dispatcher + RP |
| Side-by-side validation gate + corpus runs | 1-2 | After prompt |
| Bug-fix iteration on validation findings | 1-2 | After validation |

**Realistic remaining: 7-11 sessions to MVP.**

"Fully sellable" (per `project_ship_ready_strategy.md`) additionally
depends on V3-B Auto-RP Step 2 (Anthropic SDK semantic scoring), which
is BLOCKED indefinitely by `feedback_no_sdk_until_bank_deploy.md`. That
gate is a business decision, not a code milestone.

## Open items the user can tackle next

### Option 1 — Dispatcher Slice B (Recommended; small, close to done)

Build the counterparty-extraction wiring that joins
`counterparty_ledger` entries to transaction row indices, then thread
through `classify_transactions(counterparty_lookup=...)`. After this,
C26/C27 fires on real corpus data and unclassified rate drops
meaningfully.

Roughly 1 session. Self-contained, no external dependencies. Picks up
exactly where Slice A left off and the dispatcher's design hooks are
already in place.

### Option 2 — RP foundation sprint (Highest leverage; bigger commitment)

Rebuild RP3 scanner + RP6 constants in Track 2 independently of Track 1
(the Track 1 RP3 code lives in `kredit_lab_classify.py` which is
frozen). Then build RP2/5/7/8 from v3.5.6 prompt spec.

2-3 sessions for the foundation alone. Unlocks five categories (C01,
C02, C03, C04, C10, C11) and three dispatcher rungs plus M7 RP-name
stamping. This is the chokepoint that gates the most downstream work.

### Option 3 — Dispatcher Slice C (full v6.3.5 result orchestrator)

`build_track2_result(transactions, ledger)` returning the complete
v6.3.5-schema result dict (flags + statutory + monthly + observations +
top_parties + etc.). Roughly 2-3 sessions. Should follow Slice B
because the orchestrator wants the counterparty wiring.

### Smaller alternative — MYTUTOR-shape business-model signal (still on the queue)

Small composition (~1 session) using `COMMISSION_BLOCK_RE` + existing
transfer counting. v3.3.1 `trigger_signal`: when commission_keyword
count > 20% of individual-transfer DR volume at the pre-analysis gate,
pause and ask the user to confirm employment model. Visible-impact and
isolated. Lower leverage than the dispatcher or RP foundation.

### Blocked items (unchanged from s12)

- **C01 / C02 own-party** — blocked on BUG-003. The s12 own-account
  guard inside `is_salary_payment` covers the C05 self-suppression
  case; full C01/C02 fire-on-own-counterparty waits.
- **C03 / C04 RP detection (RP2/5/6/7/8)** — blocked on RP foundation.
- **C10 / C11 deterministic** — partly depends on RP foundation.
- **CIMB AI_ASSIST individual salary branch (C05)** — blocked on SDK
  integration decision per `feedback_no_sdk_until_bank_deploy.md`.

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 58bd456..HEAD                 # s13 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 687 / 687
```

Expected output of the last command:
```
Ran 687 tests in 0.0XXs
OK
```

The `git log` should show:

```
154d953 Track 2 session 13: per-row dispatcher Slice A (Tier 2)
3890f98 Track 2 session 13: false-negative spot-check script for s12 calibration
58bd456 prompts: Track 2 session-13 handoff (after session 12)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

Seventh recurrence since session 7. Mid-session-13 `parser-fix-mbb-
rollover-rhb-monthly` flipped the branch under us; the parallel session
completed and returned. Two s13 commits landed cleanly on top.

Durable mitigation:
`git worktree add ../Bank-Statement-Track2 track-2-development`
(creates a sibling physical checkout dedicated to Track 2). User has
declined seven times now — only offer again if it bites harder.

## Architecture rules (re-read before any code)

- **Track 1 files frozen indefinitely:**
  - `kredit_lab_classify.py`
  - `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`
  - `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`
- Track 2 must NOT import from Track 1 classifier code, and vice versa.
- Parsers and `core_utils` are SHARED infrastructure. Improvements to
  either benefit both tracks — but Track 2 sessions don't *initiate*
  parser/core_utils edits unless the user explicitly approves.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.
- **Deliberate v3.5 divergences locked through s13:**
  - `COMMISSION_BLOCK_RE` matches plural/past-tense/gerund English
    commission forms (s11). Documented in regex comment.
  - `OWN_ACCOUNT_BLOCK_RE` is a Track 2 extension (s12); not in v3.5 /
    v3.3.1 literal text but within the "no employer payroll" spirit.
  - `SUBTHRESHOLD_TOTAL_SALARY_RM` / `CHANNEL_BLIND_*` thresholds are
    Track 2 calibration constants (s12); not in v3.5. Tunable. See
    `project_track_2_statutory_calibration.md` memory.
  - Dispatcher priority follows v3.5 `classification_order` LITERALLY
    (C25 → [C01/C02] → C05 → [C03/C04] → C06-C09 → [C10-C12] →
    C13-C20 → C24 → [C26/C27]). Track 1's `classify_transactions`
    has a different order (C01/C02 before C05); Track 2's is the
    spec-literal one. Documented in `CANONICAL_CATEGORIES`.

## Out of scope for the next session

- Don't edit Track 1 files (see architecture rules).
- Don't run `git add -A` / `git add .` / `git stash` — stage Track 2
  files explicitly by path.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session. There is a real `app.py` conflict; most
  of the divergence is duplicate cherry-picks. Track 2 work continues
  on the diverged base.
- Don't push to origin without explicit user approval. (User confirmed
  2026-05-11: "no need to push to origin yet". **Ten Track 2 commits**
  + three handoffs sitting local since.)

## Memory entries that should already be loaded

The user's auto-memory pulls these on session start (verify relevance,
refresh from code if stale):

- `project_track_2_architecture.md` — the 2026-05-01 thin-AI decision.
- `project_track_2_session7_scope.md` — locked s7 scope; queue mostly
  shipped, keep the architectural reasoning.
- `project_track_2_schema_divergence.md` — net_totals schema-vs-Track-1
  divergence; verify pipeline must whitelist.
- `project_track_2_statutory_calibration.md` — threshold rationale +
  AND-gate margin (s12 + s13 verified). **NEW since s12 handoff.**
- `project_track_2_branch_drift.md` — parallel-session pattern; user
  declined worktree mitigation 7× now. **NEW since s12 handoff.**
- `feedback_handoff_vs_architecture.md` — when handoff and memo
  disagree, defer to memo and surface the choice.
- `feedback_track_isolation_design.md` — Track 1 vs Track 2 file
  isolation principle.
- `feedback_no_sdk_until_bank_deploy.md` — file-based handoff to
  claude.ai for now; no SDK integration yet.
- `feedback_auto_merge_solo.md` — ship verified fix branches by direct
  merge to main + sync derivative; don't ask about PR flow. **NEW
  since s12 handoff.**
- `project_ship_ready_strategy.md` — target = fully sellable; V3-B
  Auto-RP Step 2 is the biggest rate lever, blocked on bank-deploy
  decision.

If any are missing or seem stale, refresh from the actual code —
memory records are point-in-time snapshots and the truth is in the
repo.

## Suggested first action for the next session

Pick from:

1. **Dispatcher Slice B** — 1 session, self-contained. Wires
   counterparty extraction so C26/C27 fires on real corpus data.
   Highest "close-to-done" leverage. User's s8-s13 pattern of picking
   the "low-risk-and-unblocked-first" item points here.
2. **RP foundation sprint** — 2-3 sessions, highest downstream
   leverage but bigger commitment. Unlocks C01-C04 / C10-C11 /
   factoring / M7 stamping all at once.
3. **MYTUTOR-shape commission-ratio signal** — small, isolated,
   visible-impact (~1 session). Lower leverage than either above.

Option 1 fits the established cadence and gets the dispatcher to a
"useful on real data" state without requiring the RP foundation. Then
Option 2 in the session after when the foundation work is the
remaining chokepoint.
