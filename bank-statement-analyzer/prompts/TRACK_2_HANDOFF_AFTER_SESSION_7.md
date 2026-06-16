# Track 2 handoff — picking up after session 7

State at end-of-session-7 (2026-05-10). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `38b021f` (six new commits
this session, all on top of `c8b44f8` from session 6).

**Test count:** 252 / 252 (was 147 at session start; +105 new across
seven new test files). Run `python -m unittest discover tests` to
verify.

**Six commits added this session, all Tier 2 keyword + formula ports:**

| Commit | Port(s) | Tests | Side | Flag |
|---|---|---|---|---|
| `3e5c862` | C17 cash deposit | 14 | CR | Flag 5 |
| `98fcdcc` | C18 cash withdrawal | 13 | DR | — |
| `7654702` | C19 cheque deposit + C20 cheque issue | 23 | CR + DR | — |
| `a8d92fe` | C24 bank fees | 17 | DR | — |
| `e5e3178` | C13 reversal credits + C16 inward returns | 23 | CR | — |
| `38b021f` | net_totals formula (schema-correct) | 15 | aggregator | — |

All seven new functions live in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); test
files under [tests/](../tests/).

## Cumulative state across sessions 1-7

**Functions ported (sixteen total):**
- `compute_monthly_eod` (s1), `compute_risk_flags` + `CANONICAL_FLAGS`
  (s2), `compute_statutory_compliance` (s3), `compute_round_figure_credits`
  / `compute_large_credits` / `compute_high_value_credits` (s4),
  `compute_returned_cheques` / `compute_data_completeness` /
  `compute_fx_totals` + `is_fx_transaction` (s5),
  `compute_monthly_aggregates` (s6).
- **NEW in s7:** `compute_cash_deposits` (C17), `compute_cash_withdrawals`
  (C18), `compute_cheque_deposits` (C19), `compute_cheque_issues` (C20),
  `compute_bank_fees` (C24), `compute_reversal_credits` (C13),
  `compute_inward_returns` (C16), `compute_net_totals` (formula).

**Flag coverage:** 12 of 16 lit by Track 2 (unchanged this session — C17
already wired Flag 5 in session 2 reducer; the other s7 ports populate
schema fields not consumed by the 16-flag list).

## Mid-flight state — DO NOT TOUCH

The working tree currently has uncommitted modifications and untracked
items from **other workstreams**:

- `scripts/sprint6_impact.py`, `scripts/sprint6_raw_gaps.py`,
  `scripts/validate_keywords.py` — modified ~2026-05-07 09:34, predate
  the parser-hlb branch's HLB commit by a day. Unrelated to Track 2.
- A pile of untracked directories under `Bank-Statement/`,
  `audit_reports/`, `bank-statement-analysis-HTML-fresh/`,
  `validation runs - json/...`, plus untracked prompt docs
  (`PARSER_RHB_EXTRACTION_HANDOFF.md`, `PARSER_UOB_HANDOFF_2026-05-05.md`,
  `RUN_INPUT_FILLED_WAJA.md`) and the verify script
  `scripts/verify_ab_nov.py`. None of these are Track 2 artifacts.

**Rule:** stage Track 2 work explicitly by path
(e.g. `git add kredit_lab_classify_track2.py tests/<file>`). Never
`git add -A` / `git add .` / `git stash`. Hands off the dirty + untracked
state above.

**One Track-2 artifact is sitting untracked from earlier today:**
`scripts/track2_aggregates_spotcheck.py` — produced for Item A
(Felcra real-data spot-check that confirmed `compute_monthly_aggregates`
matches PDF footers and the session-1 EOD baseline). Worth committing as
its own small commit in the next session, or folded into the next
session's first commit.

## Critical findings from session 7

### RP-list plumbing investigation (read-only, done 2026-05-10)

The locked session-7 scope envisioned RP code ports as straightforward
Tier 3 algorithmic ports. **They are not — most are fresh builds, not
ports.**

| Component | Where | Track 2 access |
|---|---|---|
| `build_counterparty_ledger` (input source) | `app.py:4541` | ✓ shared, importable |
| `scan_related_party_candidates` + `auto_confirmed_related_parties` (RP3 scanner) | `kredit_lab_classify.py:441,480` | ✗ Track 1 frozen, NOT importable |
| `_RP_EXCLUDE_NAMES` / `_RP_EXCLUDE_PREFIXES` (RP6 partial) | `kredit_lab_classify.py:307` | ✗ Track 1 frozen, NOT importable |
| RP2 / RP5 / RP7 / RP8 logic | nowhere in engine — only in `SYSTEM_PROMPT_v3_5_6.md` | n/a — fresh builds |

The architecture memo's "Tier 3 algorithmic ports" framing for RP rules
is partially aspirational. Only RP3 (partial) and RP6 (partial exclusion
list) have any engine code; RP2/5/7/8 exist as paragraphs in the v3.5.6
prompt and need to be designed and built from scratch. Plus the partial
RP3 + RP6 code is in Track 1 frozen file, so Track 2 must rebuild
independently per the architecture's hard rule.

**Implication:** RP work has a 1-2 session foundation cost (rebuild RP3
scanner + RP6 constants in Track 2) before the first user-visible RP
rule lands. Bigger sprint than the locked scope assumed.

**Decision (path A, user-confirmed 2026-05-10):** defer RP to its own
dedicated 2-3 session sprint with a properly-scoped budget. Continue
filling session 7 with unblocked Tier 2 work instead.

### Schema-vs-Track-1 net_totals divergence (intentional, user-confirmed)

Track 1's `net_credits` / `net_debits` implementation
(`kredit_lab_classify.py:965-969`, frozen) does NOT match the v6.3.5
schema:

| Formula | v6.3.5 schema (Track 2) | Track 1 actual | Delta |
|---|---|---|---|
| net_credits exclusions | C01 + C03 + C10 + C12 + C13 + C16 | C01 + C03 + C10 + C13 | Track 1 missing C12 + C16 |
| net_debits exclusions | C02 only | C02 + C04 + C11 | Track 1 has extra C04 + C11 |

Schema v6.3.2 explicitly notes "C04 NO LONGER excluded" and "Returned
cheques are NOT excluded as they naturally net off." Track 1 missed
those updates and is frozen, so the bug stays in Track 1.

**Track 2 follows the schema literally** (commit `38b021f`).
Side-by-side validation against Track 1 will surface a delta on
consolidated.net_credits and consolidated.net_debits — that delta is an
intentional Track 2 improvement, not a regression. The verify pipeline
must explicitly whitelist this divergence. See memory entry
`project_track_2_schema_divergence.md` for the full reasoning so future
sessions don't accidentally "fix" Track 2 to match Track 1.

## Open items the user can tackle next

### Unblocked Tier 2 work (small ports, ~30-60 min each)

- **Schema validation hard gate** — pure validator: given a Track 2
  result dict, check shape against `BANK_ANALYSIS_SCHEMA_v6_3_5.json`.
  Independent, useful for integration testing.
- **Counterparty normalisation (PLANWORTH/JANM merges)** — name
  canonicalisation for the ledger output. Reduces RP false-positives
  when the foundation lands later.
- **Ghost-verb suppression** — filter generic verb-only counterparties
  ("TRANSFER FR A/C", "PAYMENT TO A/C") that are parser dropouts, not
  real entities. Cleans top-payer/payee lists.
- **JomPAY biller-code guard** — predicate function. Returns True when
  description is JOMPAY + biller code only (no entity name). Used by a
  future dispatcher to suppress C06-C09/C11 classification on those
  rows.
- **C26 / C27 corporate-suffix detection** — basic SDN BHD / BHD /
  BERHAD / TRADING / etc. detection only. Per-vertical override (clinic
  / tuition / services) stays in prompt per Tier 4. Affects trade-
  income classification.

### Unblocked Tier 2 work (medium effort)

- **IBG / DuitNow return pairing (±5 business day window)** — temporal
  pairing within input rows. Outward DR + return CR within ±5 business
  days are paired (DR→C13, CR→C16). Self-contained but requires
  business-day arithmetic. Feeds Flag 13 Data Quality.

### Larger Tier 2 work (needs aggregator pipeline)

- **C06 / C07 / C08 / C09 statutory keyword detectors** —
  `compute_statutory_compliance` (session 3) consumes monthly aggregates
  with `statutory_epf` / `statutory_socso` / `statutory_tax` /
  `statutory_hrdf` already populated. The detectors that produce those
  per-row tags are not yet ported. Bigger surface area than the simple
  CR/DR keyword ports done so far — needs a dispatcher / monthly
  aggregator first.

### Blocked items

- **C01 / C02 own-party** — blocked on BUG-003
  (`normalize_company_suffix` in `core_utils.py`) landing.
- **C03 / C04 RP detection (RP2/5/6/7/8)** — blocked on RP foundation
  sprint (rebuild RP3 scanner + RP6 constants in Track 2 independently
  of Track 1, then build RP2/5/7/8 from v3.5.6 prompt spec). Allow 2-3
  sessions for the foundation alone.
- **C10 / C11 deterministic** — partly depends on RP foundation (the
  C02+C11 dual-tag and director-personal-loan distinction need the
  resolved RP list).

### Sessions 9+

- **`SYSTEM_PROMPT_TRACK2_v0_1.md`** — the thin Tier 4 prompt (memo
  estimate ~150-200 lines vs Track 1's 831). Drafted after RP foundation
  + remaining Tier 2 ports are done.
- **Side-by-side validation gate** (`verify_*_v3a.py` regression suite
  or successor) — must pass on all 6 corpora before Track 2 ships.
- **Track 2 dispatcher** — orchestrator that calls each `compute_*` in
  priority order and assigns category tags per row. Wires up the
  per-row classification side that the function ports leave to the
  caller.

## First commands the next session should run

```bash
git status --short                                    # confirm clean / known-dirty
git branch --show-current                             # MUST be track-2-development
git log --oneline c8b44f8..HEAD                       # confirm 6 session-7 commits present
python -m unittest discover tests 2>&1 | tail -5      # confirm 252/252
```

Expected output of the last command:
```
Ran 252 tests in 0.00Xs
OK
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

Earlier in this session the working tree was flipped to
`parser-hlb-2026-05-08` and then to `main` mid-session by an external
process — turned out to be a parallel Claude Code session the user was
running on Track 1 / parser work. **There is only one physical worktree
at this directory.** If the user opens a parallel Claude session and
that session does any `git checkout`, this session's branch will flip
under it.

**Mitigation options:**
1. Time-share — only one Track 2 / Track 1 session active at a time.
2. `git worktree add ../Bank-Statement-Track2 track-2-development` —
   creates a sibling physical checkout dedicated to Track 2 so the two
   sessions stop fighting over branch state. ~10 seconds to set up.

## Architecture rules (re-read before any code)

- **Track 1 files frozen indefinitely:**
  - `kredit_lab_classify.py`
  - `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`
  - `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`
- Track 2 must NOT import from Track 1 classifier code, and vice versa.
- Parsers and `core_utils` are SHARED infrastructure (both tracks
  consume the same canonical row data). Improvements to either benefit
  both tracks — but Track 2 sessions don't *initiate* parser/core_utils
  edits unless the user explicitly approves.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.

## Out of scope for the next session

- Don't edit Track 1 files (see architecture rules).
- Don't run `git add -A` / `git add .` / `git stash` — stage Track 2
  files explicitly by path.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't push to origin without explicit user approval.

## Memory entries that should already be loaded

The user's auto-memory should pull these on session start (verify
relevance, refresh from code if stale):

- `project_track_2_architecture.md` — the 2026-05-01 thin-AI decision.
- `project_track_2_session7_scope.md` — locked session-7 scope and
  memo-literal RP split (updated 2026-05-10 with the plumbing finding).
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
