# Track 2 handoff — picking up after session 14

State at end-of-session-14 (2026-05-13). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `174b734`. One Track 2
commit in session 14 since the previous handoff (`e62bec0`).

**Test count:** 719 / 719 (was 687 at session 13 end; +32 across one
commit, all session 14). Run `python -m unittest discover tests` to
verify.

**One Track 2 commit added since the s14 handoff:**

| Commit | Function(s) / file | Tests | Role |
|---|---|---|---|
| `174b734` | `build_counterparty_lookup_track2`; `_is_synthetic_counterparty_label`; `_ledger_join_key`; `_SYNTHETIC_COUNTERPARTY_LABELS`; `_SYNTHETIC_COUNTERPARTY_RE` | 32 | Per-row dispatcher Slice B — counterparty-lookup wiring (s14) |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); new
tests in `tests/test_track2_counterparty_lookup.py` (5 new classes).

## What session 14 unblocked

**The dispatcher's C26 / C27 rung now fires on real corpus data.**
`build_counterparty_lookup_track2(transactions, counterparty_ledger)`
joins the upstream ledger back to per-row enumeration indices and
returns a `dict[int, str]` suitable for direct use as the
`counterparty_lookup=` kwarg of `classify_transactions`.

**Join semantics.** The lookup is keyed on
`(date, description, rounded amount, "CREDIT"|"DEBIT")` — the same
fingerprint shape `build_counterparty_ledger` (in `app.py`) emits per
ledger transaction. Two canonical rows that share that fingerprint map
to the SAME counterparty group by construction, so collisions resolve
correctly.

**Filtering at build time.** Synthetic / protected counterparty labels
(`UNIDENTIFIED`, `UNCATEGORIZED`, `BULK SALARY`, `CASH DEPOSIT`,
`LOAN REPAYMENT`, `KWSP`, `SOCSO`, …, plus the rail-agnostic
`UNNAMED <BANK> TRANSFER (CR|DR)`, `UNNAMED INTERNAL PAYROLL (CR|DR)`,
`CARD POS (...)`, `Unidentified (Cheque)`) are dropped at the
build-lookup stage instead of being filtered inside
`has_corporate_suffix`. This keeps the lookup semantic:
"this row has an identified third-party counterparty name".
Natural-person suppression remains the dispatcher's responsibility via
`has_natural_person_marker`.

**Slice B corpus sanity-run (2026-05-13):**

| File | tx | ledger_cps | lookup_size | Slice A | Slice B | Δ |
|---|---|---|---|---|---|---|
| Maybank Hydrise | 1013 | 396 | 1005 | 28.5% | 29.6% | +11 C27 |
| Maybank Zaim | 2688 | 531 | 2368 | 1.6% | 7.2% | +132 C26, +19 C27 |
| MBB Shahnaz Builders | 181 | 82 | 164 | 13.3% | 14.9% | +1 C26, +2 C27 |
| Juta Kenangan UOB | 682 | 52 | 75 | — | 23.2% | 7 C26 |
| Upell UOB | 264 | 173 | 223 | — | 27.7% | 49 C26 |

**All deltas are purely `unclassified → C26/C27`.** No row that the
dispatcher previously classified differently gets reclassified — exactly
the priority semantics intended (C26/C27 are at the end of the
`classification_order` ladder).

## Critical findings / decisions from session 14

### The synthetic-label filter is a frozen mirror of `app.py`'s
`_OWN_PARTY_PROTECTED_LABELS`

`_SYNTHETIC_COUNTERPARTY_LABELS` (frozenset, 18 entries) plus
`_SYNTHETIC_COUNTERPARTY_RE` together cover:

- All 18 enumerated singleton buckets (`UNIDENTIFIED`,
  `UNCATEGORIZED`, `CASH DEPOSIT`, `CASH WITHDRAWAL`, `BANK FEES`,
  `BULK SALARY`, `FD/INTEREST`, `LOAN REPAYMENT`, `LOAN DISBURSEMENT`,
  `KWSP`, `SOCSO`, `LHDN`, `HRDF`, `REVERSAL`, `RETURNED CHEQUE`,
  `INWARD RETURN`, `JANM`, `APAYLATER`).
- `UNNAMED <BANK> TRANSFER (CR|DR)` — Sprint 6/7 rail-agnostic family
  (Alliance / OCBC / RHB / Maybank / UOB / HLB / Bank Rakyat / Public
  Bank / BIMB).
- `UNNAMED INTERNAL PAYROLL (CR|DR)`.
- `CARD POS (...)`.
- `Unidentified (Cheque)` (case-insensitive).
- `UNIDENTIFIED <suffix>` (raw-fallback variants like
  `UNIDENTIFIED 12345`).

**If `app.py`'s `_OWN_PARTY_PROTECTED_LABELS` grows a new bucket
whose literal contains a corporate suffix** (e.g. a hypothetical
`LOAN REPAYMENT BERHAD`), extend either the set or the regex —
otherwise the dispatcher's `has_corporate_suffix` will accept the
bucket label as a real corporate counterparty and C26/C27 will fire
spuriously on whole-bucket aggregates. Snapshot date: 2026-05-13.

### Track 2 still doesn't import `build_counterparty_ledger`

The helper takes a pre-built `counterparty_ledger` dict as input — it
does NOT call `build_counterparty_ledger` itself. This preserves Track
2's "no app.py / no Track 1" import hygiene and lets test fixtures (and
the eventual orchestrator) feed a hand-built ledger.

Track 2's eventual orchestrator (Slice C) will need to either:

(a) take the ledger as an input alongside transactions, or
(b) call `core_utils`-resident counterparty extraction (none currently
    exists; `build_counterparty_ledger` is in `app.py`).

Option (a) is the path of least resistance and matches the s14
helper's design. The ledger is upstream of Track 1 / Track 2 fork —
treating it as a shared input is consistent with the architecture
memo.

### Slice B is additive only — no priority-order risk

The dispatcher's `classification_order` puts C26/C27 LAST. Lookup
matches do not override earlier rungs. The corpus deltas confirm this
empirically: only the `unclassified → C26 / C27` movement is observed,
no shift in C05 / C06-C09 / C13-C20 / C24 counts.

### `Maybank Zaim` lookup_size = 2368 / 2688 (~88%); C26/C27 = 151

Zaim is the biggest mover (1.6% → 7.2%). Out of 2368 rows with an
identified counterparty, only 151 fire C26/C27 — the rest fail one of:

- `has_corporate_suffix` (most counterparties are individuals
  without `SDN BHD` / `BERHAD` / etc. in the parsed name).
- NOT `has_natural_person_marker` (sole-proprietor names with `BIN`
  / `BINTI` tokens explicitly suppress C26/C27).
- ledger row is already classified by an earlier rung (C20 cheque
  issue, C24 fees, etc.).

This is the **expected ceiling for deterministic counterparty
extraction**. The remaining unclassified rows are the territory for:

1. RP detection (C03 / C04) — blocked on RP foundation sprint.
2. Own-party self-suppression (C01 / C02) — blocked on BUG-003.
3. Tier 4 AI prompt (semantic counterparty classification, e.g.
   distinguishing payroll-to-staff CR from genuine trade CR).

### What Slice B did NOT touch

- `dispatch_transaction`'s signature is unchanged.
- `classify_transactions`'s signature is unchanged. The same kwargs
  pass through; the helper just produces the right dict to feed in.
- No app.py / core_utils edits — the ledger is consumed shape-as-is.

## Sync state vs main

Still **17 commits behind main** (was 16 at end-of-s13; one s14 Track 2
commit advanced `track-2-development` while main also advanced from
parallel parser sessions). Same `app.py` conflict; defer the merge
pending a dedicated sync session.

## Cumulative state across sessions 1-14

**Functions ported / built (38 total):**

- s1-s13 — see previous handoff for complete list (37 functions).
- **NEW in s14:** `build_counterparty_lookup_track2(transactions,
  counterparty_ledger)`; `_is_synthetic_counterparty_label`;
  `_ledger_join_key`; `_SYNTHETIC_COUNTERPARTY_LABELS` (frozenset);
  `_SYNTHETIC_COUNTERPARTY_RE` (regex).

## Mid-flight state — DO NOT TOUCH

Same as previous handoff. Working tree carries uncommitted modifications
and untracked items from **other workstreams** that have nothing to do
with Track 2.

**Rule:** stage Track 2 work explicitly by path (e.g.
`git add kredit_lab_classify_track2.py tests/<file>`). Never
`git add -A` / `git add .` / `git stash`.

## Big-picture progress

13 → 14 sessions in. Previous estimate was 7-11 remaining to MVP; with
Slice B done, **6-10 remaining** seems realistic.

**Remaining to MVP Track 2 (passes side-by-side on 6 corpora):**

| Slice | Sessions | Gates |
|---|---|---|
| Dispatcher Slice C (orchestrator producing v6.3.5 result dict) | 2-3 | — |
| RP foundation sprint (RP3 scanner + RP6 constants, then RP2/5/7/8) | 2-3 | Unblocks C01-C04, C10, C11, factoring, M7 |
| Tier 3 remainder (C10 known-factoring, C11 priority logic, C11 account-number-only) | 1 | After RP foundation |
| `SYSTEM_PROMPT_TRACK2_v0_1.md` draft (Tier 4 prompt) | 1 | After dispatcher + RP |
| Side-by-side validation gate + corpus runs | 1-2 | After prompt |
| Bug-fix iteration on validation findings | 1-2 | After validation |

**Realistic remaining: 6-10 sessions to MVP.**

"Fully sellable" depends on V3-B Auto-RP Step 2 (Anthropic SDK semantic
scoring), still BLOCKED indefinitely by
`feedback_no_sdk_until_bank_deploy.md`. Business decision, not a code
milestone.

## Open items the user can tackle next

### Option 1 — Dispatcher Slice C (Recommended; orchestrator)

Build `build_track2_result(transactions, counterparty_ledger, ...)`
returning the full v6.3.5-schema result dict (flags + statutory +
monthly + observations + top_parties + classification per row). This is
the public surface the validation gate and the eventual UI/export path
will consume.

Roughly 2-3 sessions. Self-contained (no RP dependency for the
orchestrator scaffold itself). Picks up exactly where Slice B left off:
the counterparty wiring is in place, classification is per-row, the
v3.5 net-totals breakdown is already implemented (s7), the monthly
aggregator is in (s6), statutory compliance is in (s3 / s10 / s12).
Composition + schema-shaping work.

### Option 2 — RP foundation sprint (Highest leverage; bigger commitment)

Rebuild RP3 scanner + RP6 constants in Track 2 independently of Track 1
(the Track 1 RP3 code lives in `kredit_lab_classify.py` which is
frozen). Then build RP2/5/7/8 from v3.5.6 prompt spec.

2-3 sessions for the foundation alone. Unlocks five categories (C01,
C02, C03, C04, C10, C11) and three dispatcher rungs plus M7 RP-name
stamping.

### Smaller alternative — MYTUTOR-shape business-model signal

Small composition (~1 session) using `COMMISSION_BLOCK_RE` + existing
transfer counting. v3.3.1 `trigger_signal`: when commission_keyword
count > 20% of individual-transfer DR volume at the pre-analysis gate,
pause and ask the user to confirm employment model. Lower leverage
than the dispatcher or RP foundation but visible-impact and isolated.

### Blocked items (unchanged from s13)

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
git log --oneline e62bec0..HEAD                 # s14 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 719 / 719
```

Expected output of the last command:
```
Ran 719 tests in 0.0XXs
OK
```

The `git log` should show:

```
174b734 Track 2 session 14: dispatcher Slice B counterparty-lookup wiring
e62bec0 prompts: Track 2 session-14 handoff (after session 13)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

No new occurrences in s14. Seventh recurrence was s13. Durable
mitigation:
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
- `build_counterparty_ledger` lives in `app.py` and is also shared
  infrastructure conceptually. Track 2's lookup helper consumes its
  output without importing it — the caller threads the ledger in.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.
- **Deliberate v3.5 divergences locked through s14:**
  - `COMMISSION_BLOCK_RE` matches plural/past-tense/gerund English
    commission forms (s11).
  - `OWN_ACCOUNT_BLOCK_RE` is a Track 2 extension (s12); not in v3.5 /
    v3.3.1 literal text but within the "no employer payroll" spirit.
  - `SUBTHRESHOLD_TOTAL_SALARY_RM` / `CHANNEL_BLIND_*` thresholds are
    Track 2 calibration constants (s12).
  - Dispatcher priority follows v3.5 `classification_order` LITERALLY.
  - **NEW in s14:** Synthetic-label filter is mirrored from `app.py`'s
    `_OWN_PARTY_PROTECTED_LABELS` rather than reimplemented — keep in
    sync if upstream adds new buckets.

## Out of scope for the next session

- Don't edit Track 1 files (see architecture rules).
- Don't run `git add -A` / `git add .` / `git stash` — stage Track 2
  files explicitly by path.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session. There is a real `app.py` conflict; most
  of the divergence is duplicate cherry-picks.
- Don't push to origin without explicit user approval. (User confirmed
  2026-05-11: "no need to push to origin yet". **Eleven Track 2
  commits** + four handoffs sitting local since.)

## Memory entries that should already be loaded

The user's auto-memory pulls these on session start (verify relevance,
refresh from code if stale):

- `project_track_2_architecture.md` — the 2026-05-01 thin-AI decision.
- `project_track_2_session7_scope.md` — locked s7 scope; queue mostly
  shipped, keep the architectural reasoning.
- `project_track_2_schema_divergence.md` — net_totals schema-vs-Track-1
  divergence; verify pipeline must whitelist.
- `project_track_2_statutory_calibration.md` — threshold rationale +
  AND-gate margin (s12 + s13 verified).
- `project_track_2_branch_drift.md` — parallel-session pattern; user
  declined worktree mitigation 7× now.
- `feedback_handoff_vs_architecture.md` — when handoff and memo
  disagree, defer to memo and surface the choice.
- `feedback_track_isolation_design.md` — Track 1 vs Track 2 file
  isolation principle.
- `feedback_no_sdk_until_bank_deploy.md` — file-based handoff to
  claude.ai for now; no SDK integration yet.
- `feedback_auto_merge_solo.md` — ship verified fix branches by direct
  merge to main + sync derivative; don't ask about PR flow.
- `project_ship_ready_strategy.md` — target = fully sellable; V3-B
  Auto-RP Step 2 is the biggest rate lever, blocked on bank-deploy
  decision.

If any are missing or seem stale, refresh from the actual code —
memory records are point-in-time snapshots and the truth is in the
repo.

## Suggested first action for the next session

Pick from:

1. **Dispatcher Slice C** — 2-3 sessions, self-contained scaffold.
   Composes existing s1-s14 compute helpers + the dispatcher into a
   single `build_track2_result(...)` orchestrator returning the full
   v6.3.5-schema result dict. This is the public surface validation
   needs.
2. **RP foundation sprint** — 2-3 sessions, highest downstream
   leverage but bigger commitment. Unlocks C01-C04 / C10-C11 /
   factoring / M7 stamping all at once.
3. **MYTUTOR-shape commission-ratio signal** — small, isolated,
   visible-impact (~1 session). Lower leverage than either above.

Option 1 (Slice C) fits the established cadence: pick the "close-to-
done-and-unblocked" item first, ship the scaffold, then come back for
RP. The orchestrator scaffold also makes side-by-side validation
possible against Track 1's `analyze_bank_statement` output, which is
the gate for "MVP".
