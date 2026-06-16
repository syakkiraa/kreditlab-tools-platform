# Track 2 handoff — picking up after session 20

State at end-of-session-20 (2026-05-14). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `711b0f0`. One Track 2
commit in session 20 since the s20 handoff (`98bbff3`).

**Test count:** 886 / 886 (unchanged — s20 added no code).

**One Track 2 commit added in s20:**

| Commit | File | Tests | Role |
|---|---|---|---|
| `711b0f0` | `prompts/SYSTEM_PROMPT_TRACK2_v0_1.md` (303 lines, DRAFT) | 0 | Tier 4 system prompt — thin-AI side of the engine-heavy architecture |

The prompt is documentation only; no Python touched. Memo target was
150-200 lines, actual 303 — the spread is structure/headings, not
rule density (the rule surface is intentionally thin).

## What session 20 unblocked

### Tier 4 system prompt — first draft (`711b0f0`)

`SYSTEM_PROMPT_TRACK2_v0_1.md` is the analyst-facing AI prompt for
Track 2's thin-AI flow. The deterministic engine
(`kredit_lab_classify_track2.py`, RP foundation slices 1-3 complete
after s17-s19) handles Tiers 1-3 in code; this prompt covers Tier 4
judgment items + narrative polish only.

**Scope (§3):**
- `observations.positive` / `concerns` narrative polish (8-line cap).
- `report_info.related_parties` MEDIUM-candidate triage from
  Pre-Analysis Input section 2.
- Commission cluster C05-vs-regular-expense override (RUN_INPUT 4a).
- Government-CR side override (4b).
- Per-vertical C26 prior (4c) — tuition / security / construction /
  logistics SURFACED as positives, NOT reclassified.
- Account-type override (4d).
- UNCLASSIFIED row disambiguation — surface only, no reclassification
  in v0.1.
- Parser-quality narrative (Deliverable 2).

**Hard rules (§6):** never recompute `monthly_analysis`, never re-fire
the dispatcher, never invent off-schema fields, never delete
SUB_THRESHOLD / CHANNEL_BLIND / STRUCTURAL verdicts, never pause
mid-run.

**Explicit out-of-scope for v0.1 (§7):** MEDIUM-RP row reclassification,
top_parties re-derivation, IBG return pairing, vehicle-plate C11,
cross-run findings. Surface in `observations.concerns[]` when
relevant; the engine owns the fix.

**Sanity check passed** on Hydrise engine output:
- 15 top-level keys all present.
- `validate_track2_result` returns True (v6.3.5 schema-valid).
- `classification_config.{known_factoring_entities,
  unclassified_listing_threshold}` populated.
- `observations.{positive,concerns}` seeded (2 + 4 lines on Hydrise).
- `flags.indicators` = exactly 16.
- `report_info.related_parties` populated by orchestrator's
  auto-RP merge.

Every field the prompt references exists in the engine output today.

## Critical findings / decisions from session 20

### Track 2 dispatcher is feature-complete for v3.5

After s19 Slice 3, every v3.5 `classification_order` rung except C12
fires in Track 2. The prompt is the next architectural layer; from
here the work is validation, not new code.

### The prompt expanded beyond memo target (303 vs 150-200)

The architecture memo (project_track_2_architecture.md, 2026-05-01)
estimated ~150-200 lines. The draft came in at 303. The extra ~100
lines are section structure (9 headings, hard-rules block, scope
guard, version block) and the analyst-input application order (§4)
— not classification rule surface. The rule density is closer to the
memo's vision than the raw line count suggests. v0.2 may trim
boilerplate once validation tells us what's actually needed.

### v0.1 is conservative on row-level reclassification

The prompt explicitly forbids the AI from reclassifying rows
(MEDIUM-RP, UNCLASSIFIED-large, per-vertical fee-CR). This keeps the
engine output as the deterministic anchor and avoids the
two-sources-of-truth bug class that v3.5.6 closed for
`statutory_bucket`. Downside: a few rows the v3.5.6 full-AI prompt
would have reclassified stay in their engine bucket. We'll see how
much that costs in the side-by-side run.

## Sync state vs main

Still 19+ commits behind main. Unchanged. Defer.

## Cumulative state across sessions 1-20

**Functions ported / built (77 total, unchanged from s19):**

- s1-s19 — see previous handoff for complete list.
- **NEW in s20:** prompt artifact only, no Python.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree still carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path.

## Big-picture progress

20 sessions in. Engine feature-complete; Tier 4 prompt drafted.
**0-2 sessions remaining to MVP.**

**Remaining to MVP Track 2 (passes side-by-side on 6 corpora):**

| Slice | Sessions | Gates |
|---|---|---|
| Side-by-side validation gate + corpus runs (6 files) | 0-1 | Harness exists; run + diff vs tolerance |
| Bug-fix iteration on validation findings | 0-1 | After validation |

**Realistic remaining: 0-2 sessions to MVP.**

(Optional, NOT blocking MVP:
* C12 FD/interest detector port (engine).
* v0.2 prompt trim + MEDIUM-RP reclass step.
* Streamlit / app.py wire-through to actually use Track 2 end-to-end.)

## Open items the user can tackle next

### Option 1 — Run side-by-side validation gate (Recommended)

`python scripts/track2_side_by_side.py <full_report.json>` on each of
the 6 verify corpora. Capture the diffs. Most fields are already at
exact parity (per s18 and s19 sweeps); the remaining gaps are the
documented v3.5 divergences (own-party side swap, C03/C04 ordering,
C10 keyword fallback) which are Track-1-frozen, not Track-2-broken.

About 0-1 session. Likely produces a clean "ship" verdict modulo a
1-2 bug fixes.

### Option 2 — End-to-end smoke through claude.ai

Take the Hydrise engine output JSON, paste it into a fresh claude.ai
session with `SYSTEM_PROMPT_TRACK2_v0_1.md` + filled
`RUN_INPUT_TEMPLATE.md`, see what comes back. First real-world
prompt test. About 30 min.

### Option 3 — C12 FD/interest detector port (engine slice)

Half a session. Closes the last priority-ladder gap. Defer unless
validation flags FD/interest misclassification.

### Option 4 — App.py Track 2 wire-through

The Streamlit app currently calls Track 1 only. A config flag could
let runs pick Track 1 or Track 2. About 1 session; not on the
shortest path to MVP (the MVP is the side-by-side parity gate).

### Blocked items (updated from s20 outset)

- C12 deterministic FD/interest — no detector ported (lowest priority).
- CIMB AI_ASSIST — Tier 4 prompt territory; the draft covers it
  generically via §3.4 (government CP side) and §3.5 (per-vertical
  override) for the security-services / standard-SME cases.
- C01/C02 — **DONE** (s17 marker + s18 company-root).
- C03/C04 — **DONE** (s18 Slice 2).
- C10/C11 — **DONE** (s19 Slice 3).
- Tier 4 prompt — **DONE** (s20 v0.1 draft).

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 98bbff3..HEAD                 # s20 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 886 / 886
```

Expected output of the last command:
```
Ran 886 tests in 0.0XXs
OK
```

The `git log` should show:

```
<this-handoff-commit> prompts: Track 2 session-21 handoff (after session 20)
711b0f0 Track 2 session 20: SYSTEM_PROMPT_TRACK2_v0_1.md (Tier 4 prompt draft)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

Optional sanity — re-run the harness on Hydrise to see the s19 SCF
Trade C10 fire (and confirm schema validity):

```bash
python scripts/track2_side_by_side.py "validation runs - json/claude ai prompt file/Full Report Sample (April 2026 - pre-parser-fix baseline)/Full Report Maybank Hydrise Jul25-Dec25.json"
```

You should see `loan_transactions.disbursements count t1=0 t2=1 Δ=+1`
(legitimate SCF Trade fire — expected; see s19 handoff).

## Branch-stability guard

No new occurrences in s20. Seventh recurrence was s13. Durable
mitigation: `git worktree add ../Bank-Statement-Track2
track-2-development`. User has declined seven times now — only offer
again if it bites harder.

## Architecture rules (re-read before any code)

Unchanged from previous handoffs. The s20 prompt draft follows them
all:

- Track 1 files frozen indefinitely.
- Track 2 must NOT import from Track 1. The Tier 4 prompt depends
  ONLY on CLASSIFICATION_RULES_v3_5.json, BANK_ANALYSIS_SCHEMA_v6_3_5
  .json, prompts/RUN_INPUT_TEMPLATE.md, and the
  kredit_lab_classify_track2.py engine output — no references to
  SYSTEM_PROMPT_v3_5_6.md or any Track 1 prompt.
- Parsers and `core_utils` are SHARED infrastructure.
- `build_counterparty_ledger` lives in `app.py` — Track 2 consumes
  its output as a kwarg, never imports it.
- All Track 2 code in `kredit_lab_classify_track2.py`; tests in
  `tests/test_track2_*.py`; prompt in
  `prompts/SYSTEM_PROMPT_TRACK2_v*.md`.

**Deliberate v3.5 divergences locked through s20:**

(Unchanged from s19 handoff — no new divergences added in s20.)

- COMMISSION_BLOCK_RE (s11).
- OWN_ACCOUNT_BLOCK_RE (s12).
- SUBTHRESHOLD_TOTAL_SALARY_RM / CHANNEL_BLIND_* thresholds (s12).
- Dispatcher priority follows v3.5 classification_order LITERALLY
  (s13). C05 salary above C03/C04 RP per spec.
- Synthetic-label filter mirrors app.py's _OWN_PARTY_PROTECTED_LABELS
  (s14).
- _OVERALL_STATUS_SCHEMA_MAP projects SUB_THRESHOLD / CHANNEL_BLIND
  onto schema enum at serialisation time (s15).
- observations surface SUB_THRESHOLD and CHANNEL_BLIND verdicts as
  human-readable lines (s16).
- C26/C27 → trade_income_* / trade_expense_* buckets (s17).
- OWN_PARTY_MARKER_RE parser-stamped subset (s17).
- _company_root + _own_party_match company-root path (s18 Slice 1).
- RP3 scanner + auto-RP merge + C03/C04 rung (s18 Slice 2).
- LOAN_DISBURSEMENT_RE + LOAN_REPAYMENT_RE + C10/C11 dispatcher rungs
  (s19 Slice 3). C10 keyword fallback is a Track 2-only addition.

## Out of scope for the next session

Unchanged from previous handoffs:

- Don't edit Track 1 files.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Twenty
  Track 2 commits** + eleven handoffs sitting local since 2026-05-11.

## Memory entries that should already be loaded

Unchanged from previous handoff. No new memory entries needed — s20
is fully captured in this handoff + the prompt's own version block
(§9).

If any seem stale, refresh from the actual code — memory records
are point-in-time snapshots.

## Suggested first action for the next session

Pick from:

1. **Side-by-side validation gate** — 0-1 session. Mechanical
   harness run on 6 corpora; produces the MVP-ship verdict.
2. **End-to-end smoke through claude.ai with the new prompt** —
   30 min. First real-world prompt test; surfaces any analyst-side
   ergonomic issues before the validation gate.
3. **App.py wire-through** — 1 session. Lets analysts actually run
   Track 2 from the Streamlit UI. Not on the shortest path to MVP
   but unblocks first production trial.

With Tier 4 prompt in, **#1 is the natural continuation**. The MVP
gate is one harness sweep away.
