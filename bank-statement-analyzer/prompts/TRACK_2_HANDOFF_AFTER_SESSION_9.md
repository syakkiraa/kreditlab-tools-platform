# Track 2 handoff — picking up after session 9

State at end-of-session-9 (2026-05-12). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `fa33938`. One Track 2
commit this session on top of `727051a` (the session-8 handoff doc).
Also picked up an unrelated parallel-session commit (`b9a9571 fix(app):
seed first-month opening from Maybank's "OPENING BALANCE" row`) that
landed between sessions 8 and 9 — that one is a parser/app fix, not
Track 2 work; leave it alone.

**Test count:** 431 / 431 (was 400 at session start; +31 new in one new
test file). Run `python -m unittest discover tests` to verify.

**One Track 2 commit added this session:**

| Commit | Function(s) | Tests | Source rule |
|---|---|---|---|
| `fa33938` | `pair_ibg_duitnow_returns` + `_business_days_between` + `_is_outward_ibg_duitnow_giro` + `_parse_iso_date` helpers | 31 | session-8 handoff "Unblocked Tier 2 (medium effort)" + Flag 13 Data Quality |

All four new functions live in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); the
new test file is
[tests/test_track2_ibg_duitnow_pairing.py](../tests/test_track2_ibg_duitnow_pairing.py).

## What the session-9 function does

`pair_ibg_duitnow_returns(transactions, *, max_business_days=5,
holidays=frozenset(), amount_tolerance=0.01) -> list[dict]`

Pairs outward IBG/DuitNow/GIRO debits with matching credit returns
within a configurable business-day window. Identification only — does
NOT mutate rows, does NOT emit category tags. The dispatcher (when it
lands) is responsible for any downstream tagging or aggregation.

Pairing rules:
- **DR**: `debit > 0` AND description matches `\b(IBG|DUITNOW|GIRO)\b`
  AND does NOT contain `\b(INWARD|INCOMING|RETURN|RETURNED|REFUND)\b`.
- **CR**: `credit > 0` AND same date or later than the DR AND amount
  diff (rounded to 2dp first, to absorb float artefacts like
  `100.00 - 99.99 = 0.0100000000000051`) ≤ `amount_tolerance` AND
  business days apart ≤ `max_business_days`.
- **Greedy**: DRs processed in date order; each DR claims earliest
  qualifying CR; each CR consumed at most once.

Output per pair: `dr_index, cr_index, amount, dr_date, cr_date,
business_days_apart`. Pairs sorted by `dr_index` ascending.

Two downstream consumers anticipated:
1. **Flag 13 Data Quality** — count pairs where the CR description
   does NOT contain the C16 "INWARD RETURN" keyword. That count is
   the extraction-gap signal (parser missed a return keyword).
2. **Dispatcher C16 augmentation** — optionally tag the paired CR
   with C16 even when the keyword is absent, so the row is excluded
   from net credits.

Neither consumer exists yet — they're the next session's wiring work.

## Cumulative state across sessions 1-9

**Functions ported / built (25 total):**

- s1: `compute_monthly_eod`.
- s2: `compute_risk_flags` + `CANONICAL_FLAGS`.
- s3: `compute_statutory_compliance`.
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
- **NEW in s9:** `pair_ibg_duitnow_returns`.

**Flag coverage:** unchanged at 12 / 16 lit by Track 2. Flag 13 Data
Quality gets a NEW input source (pairing-without-keyword count) but
the reducer that consumes it isn't wired yet.

## Mid-flight state — DO NOT TOUCH

Same as sessions 7 / 8. The working tree still has uncommitted
modifications and untracked items from **other workstreams**:

- `scripts/sprint6_impact.py`, `scripts/sprint6_raw_gaps.py`,
  `scripts/validate_keywords.py` — modified ~2026-05-07, predate the
  parser-hlb branch's HLB commit by a day. Unrelated to Track 2.
- Untracked directories under `Bank-Statement/`, `audit_reports/`,
  `bank-statement-analysis-HTML-fresh/`, `validation runs - json/...`,
  plus untracked prompt docs (`PARSER_RHB_EXTRACTION_HANDOFF.md`,
  `PARSER_UOB_HANDOFF_2026-05-05.md`, `RUN_INPUT_FILLED_WAJA.md`) and
  the verify script `scripts/verify_ab_nov.py`.

**Rule:** stage Track 2 work explicitly by path (e.g.
`git add kredit_lab_classify_track2.py tests/<file>`). Never
`git add -A` / `git add .` / `git stash`.

## Critical findings / decisions from session 9

### Float-precision in amount tolerance (locked-in fix)

`100.00 - 99.99` in Python float arithmetic is `0.0100000000000051`,
not `0.01`. A naive `abs(diff) > 0.01` rejects a legitimately-equal
pair. Implementation rounds `abs(cr_amount - dr_amount)` to 2dp before
comparing against `amount_tolerance`. Locked by
`test_within_default_one_cent_tolerance`. If future RP / pairing code
does similar amount comparison, copy this pattern.

### JomPAY guard CCUNEJBH false-negative — investigated, accepted

(Carried over from session 8 — re-stating for the next session.)
`is_jompay_biller_code_only("JOMPAY 1115:3000104301501 CCUNEJBH")`
returns False because the predicate's "alphabetic token >= 2 chars"
heuristic mistakes the all-alpha 8-char ref code for an entity name.
1 case out of 39 JomPAY rows in samples (2.6%). User explicitly chose
to leave as-is (2026-05-11) — downstream impact is zero because the
classifiers this guard suppresses (C06/C07/C08/C09/C11) need keywords
that aren't present in a ref code anyway. If the dispatcher reveals a
real-world cost later, the tightening rule is
`^[CD][A-Z0-9]{7}$` for 8-char ref-code shape.

### Pairing function is identification-only

`pair_ibg_duitnow_returns` does NOT mutate rows and does NOT emit
category tags. It returns pair records that the future dispatcher
consumes. Don't add a side-effecting variant — Track 2 deliberately
separates pure analyzers from the dispatcher's tagging step.

### Parallel-session branch flip happened again

Mid-session-9, the working tree was checked out to `main` by another
session, then I switched back. Same hazard the session-7 and 8
handoffs warned about. The user has so far declined to set up
`git worktree add ../Bank-Statement-Track2 track-2-development`. If
the issue keeps recurring, propose it again — it's the durable fix.

## Open items the user can tackle next

### Unblocked Tier 2 work (medium effort, one session each)

- **C06 / C07 / C08 / C09 statutory keyword detectors** — per-row
  predicates that tag EPF / SOCSO / LHDN / HRDF payments. Same shape
  as session-7 keyword ports. Once shipped, they feed the existing
  `compute_statutory_compliance` (s3) via a monthly aggregator that
  doesn't exist yet. The four detectors are independent and can each
  be a small commit (`compute_epf_payments`, `compute_socso_payments`,
  `compute_lhdn_tax_payments`, `compute_hrdf_payments`) — or shipped
  together if naming-consistent.

### Compositions that s8 + s9 primitives unlock

These wire existing primitives into outputs without new infrastructure:

- **Flag 13 Data Quality wiring** — use `pair_ibg_duitnow_returns` to
  count pairs where the CR description has no C16 keyword; that count
  feeds the Flag 13 reducer. Small, isolated.
- **`filter_ghost_counterparties` in a top_parties builder** — pure
  plumbing when the top-parties aggregator lands.
- **`canonicalise_counterparty_name` in the counterparty ledger
  reducer** so JANM CAWANGAN branches roll up before ranking.
- **`has_corporate_suffix` as C26/C27 trade-income/expense trigger**
  inside the per-row classifier when the dispatcher lands. Pair with
  `has_natural_person_marker` for the sole-prop judgment.
- **`is_jompay_biller_code_only` in the dispatcher** to short-circuit
  C06-C09/C11 on JomPAY-channel-only rows.

### Larger Tier 2 work

- **Track 2 dispatcher** — orchestrator that calls each `compute_*` in
  priority order, applies the s8/s9 predicates / canonicaliser /
  pairing at the right hooks, and assigns category tags per row.
  Single biggest unblocked item. Probably 1-2 sessions.

### Blocked items (unchanged)

- **C01 / C02 own-party** — blocked on BUG-003
  (`normalize_company_suffix` in `core_utils.py`) landing.
- **C03 / C04 RP detection (RP2/5/6/7/8)** — blocked on RP foundation
  sprint (rebuild RP3 scanner + RP6 constants in Track 2 independently
  of Track 1, then build RP2/5/7/8 from v3.5.6 prompt spec). Allow 2-3
  sessions for the foundation alone.
- **C10 / C11 deterministic** — partly depends on RP foundation.

### Sessions 11+

- **`SYSTEM_PROMPT_TRACK2_v0_1.md`** — the thin Tier 4 prompt drafted
  after RP foundation + remaining Tier 2 ports are done.
- **Side-by-side validation gate** — `verify_*_v3a.py` regression suite
  or successor; must pass on all 6 corpora before Track 2 ships.

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 38b021f..HEAD                 # session-7 endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 431/431
```

Expected output of the last command:
```
Ran 431 tests in 0.0XXs
OK
```

The `git log` should show **at least** these commits (newest first):

```
fa33938 Track 2 session 9: IBG/DuitNow return pairing (Tier 2, medium effort)
b9a9571 fix(app): seed first-month opening from Maybank's "OPENING BALANCE" row   <- not Track 2
727051a prompts: Track 2 session-9 handoff (after session 8)
f1983b1 Track 2 session 8: counterparty name canonicalisation (Tier 2)
9542bdf Track 2 session 8: C26/C27 corporate-suffix detection (Tier 2)
d6236a0 Track 2 session 8: ghost-verb counterparty suppression (Tier 2)
8fcfd2d Track 2 session 8: JomPAY biller-code guard (Tier 2)
c824075 Track 2 session 8: schema validation hard gate (Tier 2)
1cbb9d0 Track 2: spot-check script for compute_monthly_aggregates (Felcra)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

Unchanged. There is only one physical worktree at this directory. If
the user runs a parallel Claude session and that session does any
`git checkout`, this session's branch will flip under it. Happened
once during session 8, once during session 9.

Durable mitigation:
`git worktree add ../Bank-Statement-Track2 track-2-development`
(creates a sibling physical checkout dedicated to Track 2). User has
not yet opted in — offer again if the issue recurs.

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

## Out of scope for the next session

- Don't edit Track 1 files (see architecture rules).
- Don't run `git add -A` / `git add .` / `git stash` — stage Track 2
  files explicitly by path.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't push to origin without explicit user approval. (User confirmed
  2026-05-11: "no need to push to origin yet".)

## Memory entries that should already be loaded

The user's auto-memory pulls these on session start (verify relevance,
refresh from code if stale):

- `project_track_2_architecture.md` — the 2026-05-01 thin-AI decision.
- `project_track_2_session7_scope.md` — locked session-7 scope and
  memo-literal RP split. **Note:** the "session-7 sequencing" section
  is now out of date — sessions 7, 8, 9 have collectively shipped
  most of the path-A queue items (C13/C16/C17-C20/C24, schema validator,
  JomPAY guard, ghost suppression, corporate suffix, canonicalisation,
  IBG/DuitNow pairing). Memory still useful for the architectural
  reasoning, just not the queue.
- `project_track_2_schema_divergence.md` — net_totals schema-vs-Track-1
  divergence; verify pipeline must whitelist.
- `feedback_handoff_vs_architecture.md` — when handoff and memo
  disagree, defer to memo and surface the choice.
- `feedback_track_isolation_design.md` — Track 1 vs Track 2 file
  isolation principle.
- `feedback_no_sdk_until_bank_deploy.md` — file-based handoff to
  claude.ai for now; no SDK integration yet.

If any are missing or seem stale, refresh from the actual code — memory
records are point-in-time snapshots and the truth is in the repo.

## Suggested first action for the next session

Pick from:

1. **C06-C09 statutory keyword detectors** (4 small commits or 1
   bundled, medium effort, no blockers). Highest ROI — finishes the
   keyword-port phase that started in s7.
2. **Track 2 dispatcher** (larger, 1-2 sessions). Unlocks every s8/s9
   primitive's downstream impact and starts producing real
   classification output.
3. **Flag 13 Data Quality wiring** using `pair_ibg_duitnow_returns`
   (small). Visible-impact composition; converts the s9 work into a
   live flag signal.

The user's pattern in s8 / s9 has been to pick the
"low-risk-and-unblocked" item first. C06-C09 fits that pattern best.
Ask before starting if scope is unclear.
