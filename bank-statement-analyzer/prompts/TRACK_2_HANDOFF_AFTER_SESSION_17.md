# Track 2 handoff — picking up after session 17

State at end-of-session-17 (2026-05-14). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `e36510c`. Three Track 2
commits in session 17 since the previous handoff (`45da59a`).

**Test count:** 781 / 781 (was 765 at session 16 end; +16 across three
commits, all session 17). Run `python -m unittest discover tests` to
verify.

**Three Track 2 commits added since the s17 handoff:**

| Commit | Function(s) / file | Tests | Role |
|---|---|---|---|
| `1a51062` | `scripts/track2_side_by_side.py` | 0 | Side-by-side validation harness — new file |
| `8a90e6c` | `_empty_monthly_entry`; `_CATEGORY_TO_MONTHLY_BUCKET`; `_round_monthly_entry`; `_build_consolidated_track2` | +3 | C26/C27 trade aggregation in monthly + consolidated |
| `e36510c` | `OWN_PARTY_MARKER_RE`; `dispatch_transaction` C01/C02 rung | +13 | Own-party marker rung (parser-stamped subset) |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py),
[scripts/track2_side_by_side.py](../scripts/track2_side_by_side.py),
[tests/test_track2_dispatcher.py](../tests/test_track2_dispatcher.py),
[tests/test_track2_orchestrator.py](../tests/test_track2_orchestrator.py).

## What session 17 unblocked

### Side-by-side harness (`1a51062`)

`python scripts/track2_side_by_side.py <full_report.json>` drives
both Track 1 (`kredit_lab_classify`) and Track 2 (`build_track2_result`)
on the same parser-produced JSON and prints a structured diff covering:

- Top-level key inventory (all 15 shared on every corpus tested)
- monthly_analysis count + gross/net credit/debit sums
- consolidated scalars (only divergent fields surfaced; nested dicts
  collapse to a key-set summary so statutory_compliance doesn't dump
  inline)
- top_parties shared/exclusive name sets per side
- own_related_transactions + loan_transactions counts and amounts
- flags.indicators detect-verdict mismatches by indicator_id
- observations positive/concerns counts (per-line text under `--full`)
- unclassified_transactions counts

Track 1 runs with default `AnalystDecisions` (no analyst form / RP
confirmations) so the comparison is reproducible. `--out DIR` dumps both
raw outputs plus a machine-readable `diff.json` for offline inspection.

### C26/C27 trade aggregation gap (`8a90e6c`)

The harness's first run reported `total_trade_*` fields as 0 across
every corpus. Empirical trace through `dispatch_transaction` showed
the rung fires correctly (11 C27 hits on Hydrise) — the gap was that
`_build_consolidated_track2` and `_empty_monthly_entry` never carried
the `trade_income_*` / `trade_expense_*` fields, so dispatched rows
had nowhere to land.

Fix: 4 new keys on monthly_analysis, C26/C27 routed through the
existing `_CATEGORY_TO_MONTHLY_BUCKET` map, 4 new totals on
consolidated. v6.3.5 schema doesn't enforce these via `required[]`
but the v6.3.4 preamble explicitly added them to schema_fields and
Track 1 emits them — needed parity for the harness to be honest.

### C01/C02 own-party marker rung (`e36510c`)

Spot-check on Upell's C26 over-fires (49× / RM 2.42M vs Track 1's
25× / RM 78k) showed all 24 t2-only fires were on rows whose
counterparty_name carries the upstream parser-stamped `(OWN-PARTY)`
marker. Track 1 catches them via company-root matching → C01; Track 2
had no own-party rung at all, so they fell through to C26.

The marker is a deterministic upstream signal (stamped by
`build_counterparty_ledger` when a counterparty's root matches the
statement's company), independent of the RP3 scanner. Landing this
rung now does NOT unblock the broader BUG-003 RP foundation work —
it just covers the parser-stamped subset.

The new rung lives in `dispatch_transaction` immediately after C25,
before all keyword/bucket rungs, so own-account rows carrying e.g.
"PAYMENT" or trade keywords don't mis-route. CR side fires C01, DR
fires C02. Marker regex tolerates case + whitespace + underscore
variants.

## Validated against the same 3-file corpus

Per-section deltas, before s17 → after s17:

| File | metric | before | after |
|---|---|---|---|
| Upell UOB | total_own_party_cr | 0 | RM 2,328,008 (20 C01 fires) |
| Upell UOB | total_trade_income_cr | RM 2,415,501 (49 mis-fires) | RM 87,493 (29 fires, 4 still over t1's 25) |
| Upell UOB | own_related_transactions count | 0 | 20 |
| Juta Kenangan UOB | total_own_party_cr | 0 | RM 3,789.69 (1 C01 fire) |
| Juta Kenangan UOB | own_related_transactions count | 0 | 1 |
| Maybank Hydrise | total_own_party_cr | 0 | 0 (no marker in this corpus) |
| Maybank Hydrise | total_trade_expense_dr | 0 | RM 57,788 (11 C27 fires) |

Hydrise is the test of "no false positives": no marker in its
counterparty_ledger → marker rung doesn't fire → 0 C01/C02. The 67
own-party rows Track 1 catches via company-root matching stay blocked
on the full RP foundation sprint.

## Critical findings / decisions from session 17

### Track 1 C01/C02 → side mapping is swapped (frozen, not fixing)

Surfaced by the side-by-side harness on Juta Kenangan. The single
RM 3,789.69 own-party CR row gets correctly classified as **C01** by
both Track 1 and Track 2 dispatchers, but Track 1's
`build_monthly_analysis` (kredit_lab_classify.py L892-897) accumulates
C01 into `own_party_dr` and C02 into `own_party_cr` — the opposite of
what CLASSIFICATION_RULES_v3_5.json defines (C01 = "Own Party Credit"
→ own_party_cr; C02 = "Own Party Debit" → own_party_dr). The
classifier comment at L723 says "Per CLASSIFICATION_RULES_v3_5: C01=CR,
C02=DR" — the aggregator violates its own stated convention.
`build_top_parties` at L1283-1286 has the same swap.

**NOT fixing** — Track 1 files are frozen indefinitely per architecture.
Logged in the s17 commit message and here so the next analyst who
looks at Track 1's own_party totals knows they're flipped vs the
schema spec, and so the side-by-side harness output is interpretable.

When reading harness diffs: where Track 1 reports `total_own_party_dr`
and Track 2 reports `total_own_party_cr` (or vice versa) for the same
amount, that's not a Track 2 bug — it's the Track 1 swap.

### Track 2 correctly assigns some bank fees Track 1 misroutes to C27

Hydrise: Track 1 fires 18 C27 / RM 58,260.94. Track 2 fires 11 C27 /
RM 57,788.44. The 7-row / RM 472.50 delta is rows where Track 1's
classifier doesn't have a C24 bank-fees rung in its dispatch order
above C26/C27, so e.g. "CMS - DR CORP CHG CMS - DR CORP CHG" lands as
C27 trade-expense. Track 2's dispatcher has C24 above C26/C27, so the
fee correctly lands as C24. Another Track 1-frozen finding worth
knowing about.

### Marker regex tolerates variants

`OWN_PARTY_MARKER_RE = re.compile(r"\(\s*OWN[\s\-_]?PARTY\s*\)", re.IGNORECASE)`

Today's corpora only use the exact `(OWN-PARTY)` form, but the regex
accepts `(own-party)`, `( OWN-PARTY )`, `(OWN_PARTY)`, etc. so an
upstream change to the marker convention won't silently regress the
rung.

### Marker overrides natural-person guard intentionally

If the parser stamps own-party on a name that ALSO matches the
natural-person guard (BIN/BINTI/etc.), the stamp wins. Test:
`test_marker_overrides_natural_person_guard`. Justification: the
marker is a deterministic upstream signal that should not be defeated
by a downstream heuristic. If a director-name + own-party stamp is
ever observed in the wild, this is the right behavior (it's still
own-party for net-totals purposes, even if the legal entity is
natural).

## Sync state vs main

Still 17+ commits behind main (same as end-of-s15/s16). The `app.py`
conflict is unchanged. Defer the merge pending a dedicated sync
session.

## Cumulative state across sessions 1-17

**Functions ported / built (66 total, was 60 at s16 end):**

- s1-s16 — see previous handoff for complete list (60 functions
  including the s15 orchestrator scaffold + s16 list builders).
- **NEW in s17:**
  - `OWN_PARTY_MARKER_RE` (module constant)
  - C01/C02 marker rung inside `dispatch_transaction` (no new function)
  - `total_trade_income_cr`, `total_trade_income_count`,
    `total_trade_expense_dr`, `total_trade_expense_count` consolidated
    keys (additions to `_build_consolidated_track2`)
  - `trade_income_count`, `trade_income_amount`, `trade_expense_count`,
    `trade_expense_amount` monthly keys (additions to
    `_empty_monthly_entry` + `_CATEGORY_TO_MONTHLY_BUCKET`)
  - `scripts/track2_side_by_side.py` — side-by-side validation harness
    (new file, ~470 lines): `run_track1`, `run_track2`,
    `build_diff`, `print_summary`, plus per-section `_section_diff_*`
    helpers.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree still carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path.

## Big-picture progress

17 sessions in. Previous estimate at end-of-s16 was 4-8 remaining;
with the harness in place + C26/C27 + C01/C02 marker landed, **3-7
remaining** to MVP.

**Remaining to MVP Track 2 (passes side-by-side on 6 corpora):**

| Slice | Sessions | Gates |
|---|---|---|
| RP foundation sprint (RP3 scanner + RP6 constants, then RP2/5/7/8) | 2-3 | Unblocks C01-C04 (non-marker), C10, C11, factoring, M7 |
| Tier 3 remainder (C10 known-factoring, C11 priority logic, C11 account-number-only) | 1 | After RP foundation |
| `SYSTEM_PROMPT_TRACK2_v0_1.md` draft (Tier 4 prompt) | 1 | After dispatcher + RP |
| Side-by-side validation gate + corpus runs (6 files) | 0-1 | Harness already exists; run + diff vs tolerance |
| Bug-fix iteration on validation findings | 1-2 | After validation |

**Realistic remaining: 3-7 sessions to MVP.**

## Open items the user can tackle next

### Option 1 — RP foundation sprint (Recommended)

Now THE highest-leverage move. The s17 marker rung covered the
parser-stamped subset; the remaining own-party + RP gap is everything
the harness now shows on Hydrise:

- 67 t1-only own-party rows (company-root matching, no marker)
- All C03/C04 (RP confirmations)
- C10 known-factoring disbursement (1 fire on Hydrise that t2 misses)
- C11 priority logic + account-number-only

Rebuild RP3 scanner + RP6 constants in Track 2 independently of Track 1.
Then RP2/5/7/8 from v3.5.6 prompt spec. 2-3 sessions for the
foundation alone. The s16 own_related/loan list builders + s17
marker rung integration tests are already in place — the moment the
new rungs start firing, the sections populate and the harness deltas
collapse.

### Option 2 — Run the harness against the full 6-corpus baseline

s17 only validated against 3 corpora (Juta Kenangan UOB, Upell UOB,
Maybank Hydrise). The s16 handoff lists 5 (add Maybank Zaim + UOB
Juta Kenangan Apr baseline). The MVP gate is "all 6 within
tolerance" — running the missing 3 today might surface a finding
that should land BEFORE the RP sprint starts.

About 1 session if findings emerge; ~30 min if they don't.

### Option 3 — Investigate the Upell residual C26 gap (4 fires / RM 9,548)

Track 1 fires C26 25× on Upell. Track 2 now fires 29×. The 4-row /
RM 9,548 delta is small but worth a spot-check: are these legitimate
corporate counterparties Track 1 misses, or another own-party-shape
that the marker rung doesn't catch?

About 30 min. Lower priority than RP foundation but cheap.

### Option 4 — Tier 4 system prompt draft

Same as previous handoff. Better to wait until after RP foundation
so the prompt can reference the deterministic floor it builds on.

### Smaller alternative — MYTUTOR-shape business-model signal

Same as previous handoffs — unchanged in scope.

### Blocked items (updated from s16)

- C03/C04 RP — full RP foundation
- C10 deterministic — full RP foundation
- C11 — full RP foundation (priority logic + account-number-only)
- CIMB AI_ASSIST
- C01/C02 non-marker subset (company-root matching for corpora like
  Hydrise) — RP foundation work, since `_company_root` extraction +
  normalisation is the same upstream work the RP3 scanner builds on

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 45da59a..HEAD                 # s17 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 781 / 781
```

Expected output of the last command:
```
Ran 781 tests in 0.0XXs
OK
```

The `git log` should show:

```
<this-handoff-commit> prompts: Track 2 session-18 handoff (after session 17)
e36510c Track 2 session 17 (continued): C01/C02 own-party marker rung
8a90e6c Track 2 session 17 (continued): C26/C27 trade aggregation in monthly + consolidated
1a51062 Track 2 session 17: side-by-side validation harness
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

Optional sanity — re-run the harness on one corpus to see the same
deltas this handoff reports:

```bash
python scripts/track2_side_by_side.py "validation runs - json/claude ai prompt file/Full Report Sample (May 2026 - post-parser-fix)/Upell UOB.json"
```

You should see `total_own_party_cr` ~RM 2,328,008 / 20 fires for
Track 2, and `own_related_transactions count t2=20`.

## Branch-stability guard

No new occurrences in s17. Seventh recurrence was s13. Durable
mitigation: `git worktree add ../Bank-Statement-Track2
track-2-development`. User has declined seven times now — only offer
again if it bites harder.

## Architecture rules (re-read before any code)

Unchanged from previous handoff. The s17 marker rung + harness +
trade aggregation follow them all:

- Track 1 files frozen indefinitely. (s17 surfaced two Track 1 bugs
  — C01/C02 swap and C24/C27 ordering — neither is being fixed.)
- Track 2 must NOT import from Track 1 (`kredit_lab_classify.py`).
  The harness imports Track 1 ONLY at script level for side-by-side
  comparison; Track 2 production code (`kredit_lab_classify_track2.py`)
  remains import-isolated.
- Parsers and `core_utils` are SHARED infrastructure.
- `build_counterparty_ledger` lives in `app.py` — Track 2 consumes its
  output as a kwarg, never imports it. The s17 marker rung reads the
  marker from the ledger-supplied `counterparty_name`; the marker
  itself is stamped by `app.py`'s ledger builder.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.

**Deliberate v3.5 divergences locked through s17:**

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
- observations.positive / concerns surface SUB_THRESHOLD and
  CHANNEL_BLIND verdicts as human-readable lines (s16).
- **NEW in s17:** C26/C27 → trade_income_*/trade_expense_* monthly +
  consolidated buckets, mirroring Track 1 (intentional alignment, not
  divergence). Track 1's C01/C02 → own_party_*-side swap is NOT
  mirrored — Track 2 follows the rulebook.
- **NEW in s17:** `OWN_PARTY_MARKER_RE` partial-rung — covers the
  parser-stamped subset of C01/C02. Full BUG-003 own-party detection
  (company-root matching) remains blocked.

## Out of scope for the next session

Unchanged from previous handoff:

- Don't edit Track 1 files. (Especially tempting after the C01/C02
  swap finding — DON'T. File them as TODOs for the eventual Track 1
  unfreeze, if there ever is one.)
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Sixteen Track
  2 commits** + seven handoffs sitting local since 2026-05-11.

## Memory entries that should already be loaded

Unchanged from previous handoff. No new memory entries needed — the
s17 work is fully documented in this handoff + the dispatcher
docstrings + the harness module docstring.

If any seem stale, refresh from the actual code — memory records are
point-in-time snapshots and the truth is in the repo.

## Suggested first action for the next session

Pick from:

1. **RP foundation sprint** — 2-3 sessions. Highest downstream
   leverage. Rebuild RP3 scanner + RP6 constants in Track 2; the s16
   list builders + s17 marker rung integration tests light up
   automatically as the new rungs start firing. Best ROI now that the
   marker rung is in.
2. **Run harness on the 3 missing corpora** — 30-60 min. Validates
   the s17 work against the broader baseline before RP sprint
   commits to a particular shape.
3. **Spot-check Upell residual 4-row C26 gap** — 30 min. Either
   confirms Track 2 is correct (Track 1 misses) or surfaces another
   shape worth a small rung addition.

With the marker rung + trade aggregation + harness all in, **#2 first
then #1** is the natural sequence: one short validation pass to make
sure no new shapes lurk on the missing 3 corpora, then commit to the
RP sprint with confidence about where it needs to land.
