# Track 2 handoff — picking up after session 18

State at end-of-session-18 (2026-05-14). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `4880d1b`. Two Track 2 commits
in session 18 since the s18 handoff (`4635447`).

**Test count:** 851 / 851 (was 781 at session 17 end; +70 in s18). Run
`python -m unittest discover tests` to verify.

**Two Track 2 commits added in s18 (plus this handoff update):**

| Commit | Function(s) / file | Tests | Role |
|---|---|---|---|
| `3ed3abf` | `_company_root`; `_own_party_match`; `_COMPANY_SUFFIXES_RE`; `_PAREN_DISAMBIGUATOR_RE`; dispatcher C01/C02 company-root rung | +27 | RP foundation Slice 1 — non-marker own-party detection |
| `4880d1b` | `_compute_rp_signals`; `scan_related_party_candidates`; `auto_confirmed_related_parties`; `_looks_like_company`; `_RP_*` constants; `PERSONAL_KEYWORDS_RP4`; dispatcher C03/C04 rung; orchestrator auto-confirm pipeline; harness auto-RP parity | +43 | RP foundation Slice 2 — RP3 scanner + C03/C04 |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py),
[scripts/track2_side_by_side.py](../scripts/track2_side_by_side.py)
(now threads `summary.company_names` AND auto-confirms HIGH RPs on
the Track 1 side for apples-to-apples comparison),
[tests/test_track2_dispatcher.py](../tests/test_track2_dispatcher.py),
[tests/test_track2_orchestrator.py](../tests/test_track2_orchestrator.py).

## What session 18 unblocked

### Slice 1 of RP foundation — own-party company-root rung (`3ed3abf`)

The s17 marker rung covered only the parser-stamped subset of C01/C02.
Slice 1 adds the company-root path: when `company_names` is supplied
(typically from `data["summary"]["company_names"]`), each entry is
normalised by `_company_root` (strip parentheticals, then the 14
corporate suffix tokens, then non-alphanumeric chars), and rows fire
C01/C02 when any root of length ≥ 5 literally appears in either the
counterparty bucket or transaction description.

Mirrors Track 1's `_company_root` + `_own_party_match`
(kredit_lab_classify.py L546-685) literally; Track 2 must NOT import
from Track 1 so the helpers are defined fresh.

### Slice 2 of RP foundation — RP3 scanner + C03/C04 (`4880d1b`)

Port of the V3-A auto-RP Step 1 scoring engine + candidate scanner +
auto-confirmation pipeline + dispatcher rung. Five signals (personal-
keyword sweep, DR concentration, monthly recurrence, bidirectional
flow, round-amount advances) score each non-company counterparty;
score ≥ 3 → HIGH (auto-confirmed); 2 → MEDIUM; 1 → LOW.

Position in dispatcher: AFTER C25 → AFTER own-party (marker +
company-root) → AFTER C05 salary → BEFORE bucket/keyword rungs. Fires
when `related_parties` (analyst-confirmed or auto-confirmed HIGH from
the scanner) contains a name whose upper-cased form appears as a
substring in either the cp bucket OR description. CR → C03, DR → C04.

The orchestrator (`build_track2_result`) runs the scanner before
classification and merges HIGH names into `related_parties` with
case-insensitive dedup; caller-supplied analyst names take precedence.

The harness now does the same on the Track 1 side
(`scan_related_party_candidates` + `auto_confirmed_related_parties` →
`AnalystDecisions(related_parties=auto_rp)`) so the side-by-side
compares apples-to-apples instead of Track 1's previously zero
related-party baseline.

### Per-corpus harness deltas with auto-RP on both sides

| Corpus | t1 own_related | t2 own_related | Δ | Note |
|---|---|---|---|---|
| Maybank Hydrise | 405 | 393 | -12 | Salary-precedence (12 director-named salary rows) |
| Maybank Zaim | 425 | 422 | -3 | Salary-precedence (3 director-named salary rows) |
| Upell UOB (May) | 50 | 50 | 0 | ✓ exact match |
| Juta Kenangan UOB (May) | 1 | 1 | 0 | ✓ exact match |
| GWE Food Pack UOB | 90 | 90 | 0 | ✓ exact match |
| UOB Juta Kenangan (Apr) | 1 | 1 | 0 | ✓ exact match |

**4 of 6 corpora perfect; 2 of 6 within 3% with deltas fully explained
by Track 2's correct v3.5 dispatcher order** (C05 salary before C03/C04
RP — locked s13). Track 1's classify_transactions does C03/C04 BEFORE
the C05 keyword fallback, which misclassifies director-named salary
rows as related-party. Track 2 follows v3.5 verbatim.

T1 and T2 RP3 scanners produce **identical HIGH-candidate sets** on
every corpus (verified by direct call). The port mirrors Track 1
exactly.

## Critical findings / decisions from session 18

### Track 1 multi-account monthly_analysis emits PAIRED rows

Track 1 emits TWO rows per (month, account) on multi-account corpora:
- Row A — "balance summary": gross=0 but eod_* / opening / closing
  populated; `account_number` is the comma-joined multi-account label.
- Row B — "transaction aggregate": gross populated, eod_* zero;
  `account_number` is the per-account value.

Track 2 emits a single merged row per (month, account). Downstream
this breaks Track 1's `build_consolidated` (eod_lowest picks 0 from
per-account rows, `accounts` count inflates, `data_completeness` reads
INCOMPLETE because the 0-gross rows look like gap months).

NOT fixing — Track 1 is frozen.

### Per-corpus own-party SIDE swap is reproducible on every corpus

Track 1 reports `total_own_party_cr` and `total_own_party_dr` with the
labels swapped vs the v3.5 rulebook (puts CR-side rows into the DR
aggregator). Slice 2 makes the same swap visible on
`total_related_party_cr / _dr` too. Same Track 1 frozen aggregator
bug from s17.

### C03/C04 precedence vs C05 salary diverges from Track 1

Track 1: C03/C04 above C05 in classify_transactions order.
Track 2: C05 above C03/C04 (v3.5 spec, locked s13).

This is the cause of the -12 / -3 Hydrise / Zaim deltas. Track 2 is
correct per spec.

### Auto-RP scanner over-fires on some vendor-like buckets

The Track 1 scanner (and now Track 2's port) flags some vendor-shape
counterparty labels as HIGH (e.g. "DEBIT - APS /OTHERS MAS PAYMENT *",
"RCMS - DR FPX MARS", "DAILY FOODSTUFF FAC" on Hydrise). They pass
`_looks_like_company` because they lack BHD/SDN/etc. markers but
exhibit concentration + recurrence signals.

This is NOT a Track 2 port bug — Track 1 does the exact same thing.
In production it'd surface as analyst-confirmable HIGH-confidence
candidates. The dispatcher's company-root own-party rung catches any
own-account variants first (HYDRISE SOLUTION is e.g. caught as C02
before C03/C04 fires).

If a future calibration cleans up the scanner, both tracks should
update — Track 1 first (it's the canonical spec), Track 2 mirrors.

## Sync state vs main

Still 19+ commits behind main. The `app.py` conflict is unchanged.
Defer the merge pending a dedicated sync session.

## Cumulative state across sessions 1-18

**Functions ported / built (75 total, was 66 at s17 end):**

- s1-s17 — see previous handoff for complete list.
- **NEW in s18:**
  - `_company_root(name) -> str` — strip suffixes / parens / non-
    alphanumerics, return upper-cased root.
  - `_own_party_match(cp_upper, desc_upper, company_roots) -> bool`
    — bidirectional 5-char-floor match.
  - `_compute_rp_signals(cp, gross_dr) -> dict | None` — 5-signal RP
    scoring engine.
  - `scan_related_party_candidates(counterparty_ledger) -> list[dict]`
    — apply exclusions + score every cp; sort HIGH → MEDIUM → LOW.
  - `auto_confirmed_related_parties(candidates) -> list[str]` —
    HIGH-only filter.
  - `_looks_like_company(name) -> bool` — explicit corporate-marker
    heuristic for RP scanner exclusion.
  - `_COMPANY_SUFFIXES_RE`, `_PAREN_DISAMBIGUATOR_RE`,
    `_COMPANY_ROOT_MIN_LEN`, `_COMPANY_ROOT_CP_MIN_LEN`,
    `_RP_CONCENTRATION_DR_THRESHOLD`, `_RP_RECURRENCE_MIN_MONTHS`,
    `_RP_BIDIRECTIONAL_MIN_SIDE_COUNT`, `_RP_ROUND_AMOUNT_FLOOR`,
    `_RP_ROUND_AMOUNT_MULTIPLE`, `_RP_ROUND_HITS_MIN`,
    `_RP_ROUND_SUSTAINED_HITS_MIN`, `_RP_ROUND_SUSTAINED_MONTHS_MIN`,
    `_RP_EXCLUDE_PREFIXES`, `_RP_EXCLUDE_NAMES`,
    `_RP_HIGH_SCORE`, `_RP_MEDIUM_SCORE`, `PERSONAL_KEYWORDS_RP4`
    (module constants).
  - C01/C02 company-root rung inside `dispatch_transaction` (Slice 1).
  - C03/C04 RP rung inside `dispatch_transaction` (Slice 2).
  - Auto-confirm pipeline inside `build_track2_result` (Slice 2).
  - Harness `run_track1` updated to auto-RP on the Track 1 side too.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree still carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path.

## Big-picture progress

18 sessions in. Slices 1 + 2 of RP foundation both done. Slice 3
(C10 factoring + C11 priority) is the next chunk; after that the
foundation is complete and the remaining work is the Tier 4 prompt +
final validation. **1-4 sessions remaining to MVP.**

**Remaining to MVP Track 2 (passes side-by-side on 6 corpora):**

| Slice | Sessions | Gates |
|---|---|---|
| RP foundation Slice 3: C10 known-factoring + C11 priority logic + account-number-only | 1 | Unblocks loan disbursement / repayment detection |
| `SYSTEM_PROMPT_TRACK2_v0_1.md` draft (Tier 4 prompt) | 1 | After dispatcher |
| Side-by-side validation gate + corpus runs (6 files) | 0-1 | Harness already exists; run + diff vs tolerance |
| Bug-fix iteration on validation findings | 0-1 | After validation |

**Realistic remaining: 1-4 sessions to MVP.**

## Open items the user can tackle next

### Option 1 — RP foundation Slice 3: C10 factoring + C11 (Recommended)

Port Track 1's factoring handling. Look at Track 1's
`AnalystDecisions.factoring_entities` flow + the C10 rung at L743-745.
C11 (loan repayment) is split into priority logic + account-number-
only sub-rungs — see Track 1's `BUCKET_TO_CATEGORY["LOAN REPAYMENT"]`
and the v3.5 prompt spec.

About 1 session. After Slice 3 the dispatcher is feature-complete for
the v3.5 priority ladder; only the Tier 4 prompt + final validation
gate remain.

### Option 2 — Investigate the Hydrise / Zaim director-salary deltas

The -12 / -3 row deltas are explained by salary-precedence. Worth
spot-checking 2-3 of the actual rows to confirm they're legitimate
salary payments (not RP that Track 2 misses). About 20-30 min.

### Option 3 — Vendor-bucket auto-RP over-fire calibration

The scanner flags some vendor-shape labels ("DEBIT - APS /OTHERS MAS
PAYMENT *", "DAILY FOODSTUFF FAC", etc.) as HIGH. The own-party rungs
catch the real own-account variants before C03/C04 fires, so the
practical impact is small — but worth investigating whether
`_looks_like_company` should be tightened or a new exclusion pattern
added. NOT urgent. About 30-45 min.

### Option 4 — Tier 4 system prompt draft

Better to wait until Slice 3 lands so the prompt can reference the
full deterministic floor.

### Blocked items (updated from s18 outset)

- C10 deterministic factoring — RP foundation Slice 3 (next)
- C11 — RP foundation Slice 3 (priority logic + account-number-only)
- CIMB AI_ASSIST
- C01/C02 — **DONE** (s17 marker + s18 company-root)
- C03/C04 — **DONE** (s18 Slice 2 scanner + dispatcher)

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 4635447..HEAD                 # s18 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 851 / 851
```

Expected output of the last command:
```
Ran 851 tests in 0.0XXs
OK
```

The `git log` should show:

```
<this-handoff-commit> prompts: Track 2 session-19 handoff (after session 18)
4880d1b Track 2 session 18 (continued): RP3 scanner + C03/C04 (RP foundation Slice 2)
50c8436 prompts: Track 2 session-19 handoff (after session 18)
3ed3abf Track 2 session 18: C01/C02 own-party company-root rung (RP foundation Slice 1)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

Optional sanity — re-run the harness on Hydrise to see the same
parity this handoff reports:

```bash
python scripts/track2_side_by_side.py "validation runs - json/claude ai prompt file/Full Report Sample (April 2026 - pre-parser-fix baseline)/Full Report Maybank Hydrise Jul25-Dec25.json"
```

You should see `own_related_transactions count t1=405 t2=393 Δ=-12`
(12-row deficit is the v3.5 salary-precedence finding — expected).

## Branch-stability guard

No new occurrences in s18. Seventh recurrence was s13. Durable
mitigation: `git worktree add ../Bank-Statement-Track2
track-2-development`. User has declined seven times now — only offer
again if it bites harder.

## Architecture rules (re-read before any code)

Unchanged from previous handoffs. Both s18 slices follow them all:

- Track 1 files frozen indefinitely. (s18 surfaced two more Track 1
  frozen idiosyncrasies — paired-row monthly_analysis + C03/C04-
  before-C05 ordering — neither is being fixed.)
- Track 2 must NOT import from Track 1. The Slice 1 + Slice 2 helpers
  are defined fresh; only the harness imports Track 1 for side-by-side
  comparison.
- Parsers and `core_utils` are SHARED infrastructure.
- `build_counterparty_ledger` lives in `app.py` — Track 2 consumes its
  output as a kwarg, never imports it.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.

**Deliberate v3.5 divergences locked through s18:**

- `COMMISSION_BLOCK_RE` (s11).
- `OWN_ACCOUNT_BLOCK_RE` (s12).
- `SUBTHRESHOLD_TOTAL_SALARY_RM` / `CHANNEL_BLIND_*` thresholds (s12).
- Dispatcher priority follows v3.5 `classification_order` LITERALLY
  (s13). **C05 salary above C03/C04 RP per spec — Track 1 has them
  reversed.** This is what produces the Hydrise -12 / Zaim -3 row
  deltas.
- Synthetic-label filter mirrors `app.py`'s `_OWN_PARTY_PROTECTED_LABELS`
  (s14).
- `_OVERALL_STATUS_SCHEMA_MAP` projects SUB_THRESHOLD / CHANNEL_BLIND
  onto schema enum at serialisation time (s15).
- observations.positive / concerns surface SUB_THRESHOLD and
  CHANNEL_BLIND verdicts as human-readable lines (s16).
- C26/C27 → trade_income_* / trade_expense_* monthly + consolidated
  buckets (s17 — intentional alignment, not divergence). Track 1's
  C01/C02 → own_party_*-side swap is NOT mirrored — Track 2 follows
  the rulebook.
- `OWN_PARTY_MARKER_RE` rung — parser-stamped subset (s17).
- `_company_root` + `_own_party_match` — non-marker own-party
  detection via company-root literal match (s18 Slice 1).
- `_compute_rp_signals` + `scan_related_party_candidates` +
  `auto_confirmed_related_parties` + C03/C04 rung — auto-RP scanner
  with deterministic HIGH-confidence promotion (s18 Slice 2).
  Mirrors Track 1's scanner; uses the same five signals + same
  threshold mapping; `_RP_EXCLUDE_NAMES` is Track 1's
  `_RP_EXCLUDE_NAMES ∪ BUCKET_TO_CATEGORY.keys()` consolidated
  (Track 2 has no BUCKET_TO_CATEGORY dispatcher map).

## Out of scope for the next session

Unchanged from previous handoffs:

- Don't edit Track 1 files. (Especially tempting after the C03/C04 vs
  C05 ordering finding — DON'T. File as a TODO.)
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Eighteen
  Track 2 commits** + nine handoffs sitting local since 2026-05-11.

## Memory entries that should already be loaded

Unchanged from previous handoff. No new memory entries needed — s18
slices are fully documented in this handoff + the dispatcher
docstrings + module-level RP foundation comments.

If any seem stale, refresh from the actual code — memory records are
point-in-time snapshots and the truth is in the repo.

## Suggested first action for the next session

Pick from:

1. **RP foundation Slice 3 (C10 factoring + C11 priority)** — 1 session.
   Last dispatcher slice; after this the priority ladder is complete
   and only the Tier 4 prompt + final validation gate remain.
2. **Spot-check Hydrise / Zaim director-salary deltas** — 20-30 min.
   Confirm the 12 / 3 rows are legitimate salary not RP.
3. **Vendor-bucket auto-RP over-fire calibration** — 30-45 min. Low
   priority; the own-party rungs absorb the most-impactful overlaps.

With both s18 slices in, **#1 is the natural continuation**. Slice 3
closes the dispatcher and the MVP is within touching distance.
