# Track 2 handoff — picking up after session 16

State at end-of-session-16 (2026-05-13). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `2f6dda4`. One Track 2
commit in session 16 since the previous handoff (`90e5fce`).

**Test count:** 765 / 765 (was 745 at session 15 end; +20 across one
commit, all session 16). Run `python -m unittest discover tests` to
verify.

**One Track 2 commit added since the s16 handoff:**

| Commit | Function(s) / file | Tests | Role |
|---|---|---|---|
| `2f6dda4` | `_build_own_related_transactions_list_track2`; `_build_loan_transactions_track2`; `_build_observations_track2`; `_row_amount_and_side`; `_OWN_RELATED_PRIMARIES`; `_OWN_PARTY_PRIMARIES`; `_LOAN_CATEGORY_LABELS`; `_OBSERVATION_MAX_ITEMS` | 20 | Per-row dispatcher Slice C Part 2 — orchestrator list builders (s16) |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); new
tests in `tests/test_track2_orchestrator.py` (4 new classes —
`OwnRelatedTransactionsListTests`, `LoanTransactionsListTests`,
`ObservationsTests`, `SliceCPart2EndToEndTests`).

## What session 16 unblocked

**The Track 2 orchestrator scaffold is complete.** All three previously
stubbed sections now have working builders:

- `observations.positive` / `observations.concerns` — derived from
  consolidated + statutory + flag indicators, capped at 8 each (v6.3.4
  raised the cap from 5). Today's signals: reconciliation status, net
  credits, statutory coverage / sub-threshold / channel-blind verdicts,
  unclassified residue, and AML-relevant flag indicators (returned
  cheques, round-figure CR, cash deposits).
- `own_related_transactions.transactions[]` — every C01-C04 row with
  schema-required `{date, description, amount, type, party_type}` plus
  optional `party_name` from `counterparty_lookup`.
- `loan_transactions.disbursements[]` / `loan_transactions.repayments[]`
  — C10 / C11 rows in the `$defs/transaction_entry` shape.

**Validated against the same 5-file corpus from s15 (all PASS schema):**

| File | tx | obs+ | obs- | own_rel | disb | repay |
|---|---|---|---|---|---|---|
| Juta Kenangan UOB | 682 | 2 | 3 | 0 | 0 | 0 |
| Upell UOB | 264 | 2 | 3 | 0 | 0 | 0 |
| Maybank Hydrise | 1013 | 2 | 4 | 0 | 0 | 0 |
| Maybank Zaim | 2688 | 2 | 4 | 0 | 0 | 0 |
| UOB Juta Kenangan (Apr baseline) | 682 | 2 | 3 | 0 | 0 | 0 |

The own_related and loan lists stay empty on today's corpora because
the C01-C04 / C10 / C11 dispatcher rungs are still blocked pending the
RP foundation sprint. **The orchestrator wiring is in place** — those
sections light up automatically the moment the rungs start emitting.

Sample observations (Zaim, 2688 tx):

```
positive:
  + All months reconciled to bank statements within tolerance.
  + Net credits of RM 3,349,444.24 indicate active turnover.
concerns:
  - Statutory gaps — EPF 66.67% / SOCSO 50.0%.
  - Unclassified rows: CR RM 2,418,329.07 / DR RM 2,932,650.68 — V1 deferred categories.
  - Round Figure Credits (AML): 49 round-figure credits totalling RM 1,020,000.00.
  - Cash Deposits (AML): 3 cash deposits totalling RM 8,449.00 (0.3% of gross credits).
```

## Critical findings / decisions from session 16

### Track 2-specific statutory observations

Track 2's s12 calibration introduced two extra statutory verdicts not in
the schema enum: `SUB_THRESHOLD` and `CHANNEL_BLIND`. The s15 sanitiser
projects these onto schema-valid `COMPLIANT` / `GAPS_DETECTED` for the
top-level `overall_status` field, but preserves the original verdict on
the `subthreshold_employer.is_subthreshold` /
`channel_blind_employer.is_channel_blind` extension fields.

The s16 observations builder reads those extension fields directly:

- `is_subthreshold == True` → positive line: "Sub-threshold employer —
  statutory contributions not required at this salary level."
- `is_channel_blind == True` → concern line: "Statutory payments not
  visible in this channel — compliance unverifiable from these statements
  alone."

When either fires, the standard EPF/SOCSO-coverage observation is
suppressed (otherwise we'd emit two contradictory lines for the same
salary stream).

### Loan-list entry uses `transaction_entry` $def shape

The schema `$defs/transaction_entry` requires
`{date, description, amount}` and allows optional `category, balance,
exclusion_note`. The s16 builder emits all required keys plus
`category` (always set: `"loan_disbursement"` / `"loan_repayment"`) and
`balance` when the row carries a numeric one. The v6.3.2
`exclusion_note` field is intentionally NOT set — it only applies to
dual-tagged C02+C11 rows, and Track 2's dispatcher emits one primary
tag per row (the dual-tag flow is Track 1's; Track 2 will revisit when
the RP foundation lands and decides whether to dual-tag or keep
single-primary).

### Own-related list — `party_name` is opportunistic, not derived

For C03/C04 (related-party) rows, `party_name` makes semantic sense;
for C01/C02 (own-party), it's the same entity by construction. The s16
builder reads `party_name` from the `counterparty_lookup` index → name
map (same lookup that drives the C26/C27 trade-in/out rung). When the
index has a non-synthetic name, it's added to the entry. Otherwise the
field is omitted — the schema allows that.

This is a stop-gap until the RP foundation lands a proper RP-name
attribution step. The RP sprint will likely revisit how party names get
stamped onto C03/C04 rows specifically.

### `_row_amount_and_side` infers from canonical credit/debit

Track 1's list builders read from private `_amount` / `_side` fields
that Track 2 doesn't populate. The s16 helper re-derives them from the
canonical `credit` / `debit` fields: classification.side wins if set,
else whichever of credit / debit is non-zero. Rows where neither side
has a positive amount are skipped (avoids emitting degenerate amount=0
entries).

### Observations capped at 8 per list (v6.3.4)

`_OBSERVATION_MAX_ITEMS = 8`. The cap is enforced as a hard slice at
emit time so a future expansion of signals can't accidentally overflow
the schema's `maxItems: 8`. The flag-driven concern loop checks the
cap on each iteration to short-circuit cleanly.

## Sync state vs main

Still 17+ commits behind main (same as end-of-s15). The `app.py`
conflict is unchanged. Defer the merge pending a dedicated sync
session.

## Cumulative state across sessions 1-16

**Functions ported / built (60 total):**

- s1-s15 — see previous handoff for complete list (53 functions
  including the s15 orchestrator scaffold + 10 module constants).
- **NEW in s16:** 4 new functions / helpers + 4 module-level constants:
  - `_build_own_related_transactions_list_track2`,
    `_build_loan_transactions_track2`,
    `_build_observations_track2`,
    `_row_amount_and_side` (private util).
  - `_OWN_RELATED_PRIMARIES`, `_OWN_PARTY_PRIMARIES`,
    `_LOAN_CATEGORY_LABELS`, `_OBSERVATION_MAX_ITEMS`.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree still carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path.

## Big-picture progress

16 sessions in. Previous estimate at end-of-s15 was 5-9 remaining;
with Slice C Part 2 in, **4-8 remaining** to MVP.

**Remaining to MVP Track 2 (passes side-by-side on 6 corpora):**

| Slice | Sessions | Gates |
|---|---|---|
| RP foundation sprint (RP3 scanner + RP6 constants, then RP2/5/7/8) | 2-3 | Unblocks C01-C04, C10, C11, factoring, M7 |
| Tier 3 remainder (C10 known-factoring, C11 priority logic, C11 account-number-only) | 1 | After RP foundation |
| `SYSTEM_PROMPT_TRACK2_v0_1.md` draft (Tier 4 prompt) | 1 | After dispatcher + RP |
| Side-by-side validation gate + corpus runs | 1-2 | After prompt |
| Bug-fix iteration on validation findings | 1-2 | After validation |

**Realistic remaining: 4-8 sessions to MVP.**

## Open items the user can tackle next

### Option 1 — Side-by-side validation harness (Recommended)

Build a small CLI / script that runs `build_track2_result` AND Track 1's
`analyze_bank_statement` on the same corpus file and emits a structured
diff (which keys / counts / amounts differ, and by how much). This is
the gate for "MVP" — once Track 2 is within tolerance of Track 1 on the
6-corpus baseline, it ships.

Roughly 1 session. With the orchestrator scaffold now complete (s15 +
s16), this is the natural next step. It surfaces the deltas the RP
foundation sprint needs to close — the expected divergences (Track 1
has C01/C03 fires, Track 2 has zero; Track 1's net_credits formula
differs by 2 categories per `project_track_2_schema_divergence`
memory) become a concrete checklist of "is the orchestrator producing
what it should everywhere else?"

This was Option 3 in the s16 handoff. With Slice C done it moves to
the front: it doesn't depend on further classifier work and it tells
us where the RP sprint needs to land most.

### Option 2 — RP foundation sprint (Highest leverage; bigger commitment)

Rebuild RP3 scanner + RP6 constants in Track 2 independently of Track 1.
Then build RP2/5/7/8 from v3.5.6 prompt spec.

2-3 sessions for the foundation alone. Unlocks five categories (C01,
C02, C03, C04, C10, C11) and the corresponding monthly_analysis buckets
already in place from s15. The own_related and loan list builders from
s16 light up automatically the moment these rungs start firing.

### Option 3 — Tier 4 system prompt draft

Draft `SYSTEM_PROMPT_TRACK2_v0_1.md` covering the medium-confidence
rungs that stay AI-side (per the Track 2 architecture memo). This is
work that has to land BEFORE side-by-side validation can be meaningful
on AI-side categories, but AFTER the RP foundation sprint so the prompt
can reference the deterministic floor it builds on.

Probably better to wait until after RP foundation.

### Smaller alternative — MYTUTOR-shape business-model signal

Same as previous handoffs — unchanged in scope.

### Blocked items (unchanged from s15)

Same as previous: C01/C02 own-party, C03/C04 RP, C10/C11 deterministic,
CIMB AI_ASSIST.

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 90e5fce..HEAD                 # s16 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 765 / 765
```

Expected output of the last command:
```
Ran 765 tests in 0.0XXs
OK
```

The `git log` should show:

```
<this-handoff-commit> prompts: Track 2 session-17 handoff (after session 16)
2f6dda4 Track 2 session 16: dispatcher Slice C Part 2 — orchestrator list builders
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

No new occurrences in s16. Seventh recurrence was s13. Durable
mitigation: `git worktree add ../Bank-Statement-Track2
track-2-development` (creates a sibling physical checkout dedicated to
Track 2). User has declined seven times now — only offer again if it
bites harder.

## Architecture rules (re-read before any code)

Unchanged from previous handoff. The s16 orchestrator list builders
follow them all:

- Track 1 files frozen indefinitely.
- Track 2 must NOT import from Track 1 (`kredit_lab_classify.py`).
  Slice C Part 2 re-implements the Track 1 observation / loan / own-
  related list builders from scratch rather than importing.
- Parsers and `core_utils` are SHARED infrastructure.
- `build_counterparty_ledger` lives in `app.py` — Track 2 consumes its
  output as a kwarg, never imports it.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.

**Deliberate v3.5 divergences locked through s16:**

- `COMMISSION_BLOCK_RE` (s11).
- `OWN_ACCOUNT_BLOCK_RE` (s12).
- `SUBTHRESHOLD_TOTAL_SALARY_RM` / `CHANNEL_BLIND_*` thresholds (s12).
- Dispatcher priority follows v3.5 `classification_order` LITERALLY
  (s13).
- Synthetic-label filter mirrors `app.py`'s `_OWN_PARTY_PROTECTED_LABELS`
  (s14).
- `_OVERALL_STATUS_SCHEMA_MAP` projects SUB_THRESHOLD / CHANNEL_BLIND
  onto schema enum at serialisation time, preserving the original
  verdict on extension fields (s15).
- **NEW in s16:** observations.positive / concerns surface the
  SUB_THRESHOLD and CHANNEL_BLIND verdicts as human-readable lines,
  reading from the s15 extension fields. Standard EPF/SOCSO coverage
  observation suppressed when either fires.

## Out of scope for the next session

Unchanged from previous handoff:

- Don't edit Track 1 files.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Thirteen Track
  2 commits** + six handoffs sitting local since 2026-05-11.

## Memory entries that should already be loaded

Unchanged from previous handoff. No new memory entries needed — the
s16 work is fully documented in this handoff + the orchestrator
docstrings.

If any seem stale, refresh from the actual code — memory records are
point-in-time snapshots and the truth is in the repo.

## Suggested first action for the next session

Pick from:

1. **Side-by-side validation harness** — 1 session. Highest "is the
   orchestrator actually right?" leverage. Builds a CLI/script that
   diffs Track 2 vs Track 1 output on the corpus, surfacing which keys
   / counts / amounts differ.
2. **RP foundation sprint** — 2-3 sessions. Highest downstream leverage.
   Lights up C01-C04 / C10-C11 / M7 stamping. The s16 list builders are
   already in place, so the moment the rungs start firing the sections
   populate.

With the orchestrator scaffold complete, Option 1 is the natural pick
— it surfaces a concrete punch list that informs how Option 2 should
be sequenced. The s8-s13 "low-risk-and-unblocked-first" pattern points
the same way.
