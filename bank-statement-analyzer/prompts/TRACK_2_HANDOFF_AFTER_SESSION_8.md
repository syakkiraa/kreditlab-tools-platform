# Track 2 handoff — picking up after session 8

State at end-of-session-8 (2026-05-11). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `f1983b1` (six new commits
this session on top of `38b021f` from session 7).

**Test count:** 400 / 400 (was 252 at session start; +148 new across
five new test files). Run `python -m unittest discover tests` to
verify.

**Six commits added this session — schema validator + four unblocked
Tier 2 ports:**

| Commit | Function(s) | Tests | Source rule |
|---|---|---|---|
| `1cbb9d0` | (script) `scripts/track2_aggregates_spotcheck.py` | n/a | Item A leftover from session 7 |
| `c824075` | `validate_track2_result` + `DEFAULT_SCHEMA_PATH` | 14 | v6.3.5 schema |
| `8fcfd2d` | `is_jompay_biller_code_only` | 24 | `CLASSIFICATION_RULES_v3_5.json::jompay_rule` |
| `d6236a0` | `is_ghost_counterparty` + `filter_ghost_counterparties` | 36 | schema `top_parties` v6.3.3.2 note |
| `9542bdf` | `has_corporate_suffix` + `has_natural_person_marker` | 44 | `CLASSIFICATION_RULES_v3_5.json` C26 / C27 triggers |
| `f1983b1` | `canonicalise_counterparty_name` + `canonicalise_counterparty_entries` | 30 | ranking notes (JANM, PLANWORTH) |

All eight new functions live in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); test
files under [tests/](../tests/).

## Cumulative state across sessions 1-8

**Functions ported / built (twenty-four total):**

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
- **NEW in s8:** `validate_track2_result` (schema gate),
  `is_jompay_biller_code_only`, `is_ghost_counterparty` +
  `filter_ghost_counterparties`, `has_corporate_suffix` +
  `has_natural_person_marker`, `canonicalise_counterparty_name` +
  `canonicalise_counterparty_entries`.

**Flag coverage:** unchanged at 12 / 16 lit by Track 2. The s8 ports
populate predicates and validation gates, not flag-input fields.

## Mid-flight state — DO NOT TOUCH

Same as session 7. The working tree still has uncommitted modifications
and untracked items from **other workstreams**:

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

## Critical findings from session 8

### `jsonschema` is available transitively — no requirements.txt change

`jsonschema 4.25.1` is reachable in the deployment env via
`streamlit -> altair -> jsonschema`. `validate_track2_result` imports
it locally (inside the function body) to keep module-load lightweight
and avoid pulling jsonschema into every Track 2 import path.

If a future host environment ships without it, the function raises
`ImportError` cleanly — that's the right failure mode for a hard gate.
Do NOT pin it into `requirements.txt` unless we own a Track-2-only
deployment that strips altair/streamlit out.

### `validate_track2_result` is a hard gate, not a soft validator

Returns `(is_valid, errors)` where `errors` is the **exhaustive** list
of every constraint violation (sorted by JSON path), not just the first.
Callers should treat a non-empty errors list as "the result is
unusable, fix the producer" rather than "warn and proceed". This is
deliberate — the schema is the audit-defense contract; partial
validation hides drift.

### Conservative scope on PLANWORTH GLOBAL canonicalisation

Only `PLANWORTH GLOBAL` / `PLANWORTH GLOBAL FAC` / `PLANWORTH GLOBAL
FACTORING` collapse. Anything else (e.g. `PLANWORTH GLOBAL SECURITIES`)
passes through unchanged — there's no rule saying any PLANWORTH GLOBAL
suffix is the same entity, so auto-merging would be a false positive.
The locked behaviour is asserted by
`test_planworth_global_with_unknown_trailing_unchanged`.

## Open items the user can tackle next

### Unblocked Tier 2 work (medium effort, one session each)

- **IBG / DuitNow return pairing (±5 business day window)** — temporal
  pairing within input rows. Outward DR + return CR within ±5 business
  days are paired (DR→C13, CR→C16). Self-contained but requires
  business-day arithmetic. Feeds Flag 13 Data Quality.

### Larger Tier 2 work (needs aggregator pipeline)

- **C06 / C07 / C08 / C09 statutory keyword detectors** —
  `compute_statutory_compliance` (s3) consumes monthly aggregates with
  `statutory_epf` / `statutory_socso` / `statutory_tax` /
  `statutory_hrdf` already populated. The detectors that produce those
  per-row tags are not yet ported. Bigger surface area than the simple
  CR/DR keyword ports done in s7 — needs a dispatcher / monthly
  aggregator first.

### Compositions that the s8 primitives unlock

These wire s8 primitives into the s6 / s7 outputs and need no new
infrastructure:

- **Apply `filter_ghost_counterparties` to a top_parties builder** when
  the top-parties aggregator lands. Pure plumbing; cheque-bucket flag
  passes through.
- **Apply `canonicalise_counterparty_name` in the counterparty ledger
  reducer** so JANM CAWANGAN branches roll up before ranking.
- **Use `has_corporate_suffix` as the C26/C27 trade-income/expense
  trigger predicate** inside the per-row classifier when the dispatcher
  lands. Pair with `has_natural_person_marker` for the sole-prop
  judgment call (Tier 4 prompt is responsible for the override).
- **Use `is_jompay_biller_code_only` in the dispatcher** to short-circuit
  C06-C09/C11 classification on JomPAY-channel-only rows.

### Blocked items (unchanged from s7 handoff)

- **C01 / C02 own-party** — blocked on BUG-003
  (`normalize_company_suffix` in `core_utils.py`) landing.
- **C03 / C04 RP detection (RP2/5/6/7/8)** — blocked on RP foundation
  sprint (rebuild RP3 scanner + RP6 constants in Track 2 independently
  of Track 1, then build RP2/5/7/8 from v3.5.6 prompt spec). Allow 2-3
  sessions for the foundation alone.
- **C10 / C11 deterministic** — partly depends on RP foundation.

### Sessions 10+

- **`SYSTEM_PROMPT_TRACK2_v0_1.md`** — the thin Tier 4 prompt drafted
  after RP foundation + remaining Tier 2 ports are done.
- **Side-by-side validation gate** — `verify_*_v3a.py` regression suite
  or successor; must pass on all 6 corpora before Track 2 ships.
- **Track 2 dispatcher** — orchestrator that calls each `compute_*` in
  priority order, applies the s8 predicates / canonicaliser at the
  right hooks, and assigns category tags per row.

## First commands the next session should run

```bash
git status --short                                    # confirm known-dirty
git branch --show-current                             # MUST be track-2-development
git log --oneline 38b021f..HEAD                       # confirm 6 session-8 commits present
python -m unittest discover tests 2>&1 | tail -5      # confirm 400/400
```

Expected output of the last command:
```
Ran 400 tests in 0.0XXs
OK
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

Unchanged from session 7. There is only one physical worktree at this
directory. If the user runs a parallel Claude session and that session
does any `git checkout`, this session's branch will flip under it.

Mitigation: time-share OR
`git worktree add ../Bank-Statement-Track2 track-2-development`.

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
- Don't push to origin without explicit user approval.

## Memory entries that should already be loaded

The user's auto-memory pulls these on session start (verify relevance,
refresh from code if stale):

- `project_track_2_architecture.md` — the 2026-05-01 thin-AI decision.
- `project_track_2_session7_scope.md` — locked session-7 scope and
  memo-literal RP split.
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
