# Track 2 handoff — picking up after session 12

State at end-of-session-12 (2026-05-12). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `42d3bfe`. Three Track 2
commits in session 12 since the previous handoff (`c49b136`). One
unrelated parallel-session commit interleaved (`480d307 docs: parser
audit v2.1 — fold in auditor pushback on overhead`) — leave alone.

**Test count:** 639 / 639 (was 594 at session 11 end; +45 across three
commits, all session 12). Run `python -m unittest discover tests` to
verify.

**Three Track 2 commits added since the s11 handoff:**

| Commit | Function(s) | Tests | Role |
|---|---|---|---|
| `14baecd` | `OWN_ACCOUNT_BLOCK_RE`; updated `is_salary_payment` | 6 | C05 own-account / inter-account guard (s12) |
| `59d804e` | `SUBTHRESHOLD_TOTAL_SALARY_RM`, `is_subthreshold_employer`; new `SUB_THRESHOLD` overall_status branch in `compute_statutory_compliance`; Flag 6/7 latent 0% fallback fix; `subthreshold_employer` indicator on output | 19 | Sub-threshold employer branch (s12) |
| `42d3bfe` | `CHANNEL_BLIND_CHEQUE_DR_MIN_RM`, `CHANNEL_BLIND_CHEQUE_DR_MIN_RATIO`, `CHEQUE_DR_HEURISTIC_RE`, `compute_channel_blind_indicator`; new `CHANNEL_BLIND` overall_status branch; optional `transactions=` kwarg on `compute_statutory_compliance`; `channel_blind_employer` indicator on output; Flag 6/7 remark routing | 20 | Cheque-channel modulation (s12) |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); new
tests added to `tests/test_track2_salary.py` (one new class) and
`tests/test_track2_statutory.py` (six new classes).

**Co-authored-by trailer:** `59d804e` and `42d3bfe` carry it; `14baecd`
does not (missed convention on the first s12 commit). Per the
no-amend rule it was left as-is. Cosmetic; not blocking.

## What session 12 unblocked

**The statutory chain CRITICAL-verdict bias is calibrated.** The s11
Layer-2 corpus run produced 5 CRITICAL verdicts on the named accounts
(Hou Tian / Juta Kenangan / HLB MTCE / RE Concept / Calvin Skin). All
five were grounded against their actual PDFs and parser output. The
breakdown:

| Account | Before s12 | After s12 | Cause |
|---|---|---|---|
| HLB MTCE | CRITICAL | **COMPLIANT** | s12 own-account guard cleared 2 inter-account salary FPs |
| RE Concept | CRITICAL | **SUB_THRESHOLD** | RM 11.8K total payroll, 2 payees → sub-threshold employer |
| Calvin Skin | CRITICAL | **SUB_THRESHOLD** | RM 15.25K total, director-only → sub-threshold |
| Juta Kenangan | CRITICAL | **CHANNEL_BLIND** | 90.7% cheque-DR (RM 24.2M); statutory likely cheque-paid |
| Hou Tian | CRITICAL | **CHANNEL_BLIND** | 24.9% cheque-DR (RM 1.66M); same shape |

5/20 CRITICAL → 0/20 CRITICAL on the s11 named accounts. The chain
itself was correctly wired (s10+s11 work) but inherited three distinct
false-positive classes from upstream input quality — each addressed by
one of the three s12 commits.

**Verdict taxonomy now in `compute_statutory_compliance`:**

```
overall_status priority (highest beats lower):
  SUB_THRESHOLD    — sole-prop / director-only / sub-threshold employer
                     (total salary <= RM 30,000); no employer obligation
                     assumed, 0% coverage may be correct
  CHANNEL_BLIND    — cheque-DR >= RM 500K AND >= 10% of gross DR;
                     statutory may be paid via cheque or off-account
                     and not detectable by keyword
  CRITICAL         — salary active AND (EPF or SOCSO coverage = 0%)
  GAPS_DETECTED    — partial coverage
  COMPLIANT        — full coverage or no salary obligation
```

Sub-threshold wins over channel-blind because "no obligation" is a
stronger statement than "obligation may exist but invisible". Both are
softer than CRITICAL.

## Critical findings / decisions from session 12

### Flag 6 / 7 0% fallback bug — fixed inline in `59d804e`

`compute_risk_flags` was using `float(... or 100)` for the coverage
fallback. `0.0 or 100` evaluates to `100` because 0.0 is falsy in
Python, so 0% coverage was silently being treated as 100% — Flags 6/7
never fired on the most common CRITICAL case. Replaced with an explicit
`None` check so 0.0 stays 0.0. Pre-existing latent bug that would have
masked the s12 calibration output if left uncorrected; fixed in the
same commit because the new SUB_THRESHOLD remark wiring depended on
Flags 6/7 actually firing.

### C20 `compute_cheque_issues` doesn't match UOB / Maybank cheque withdrawal shapes

`CHEQUE_ISSUE_RE` (`HOUSE CHQ DR` / `CLRG CHQ DR` / `INWARD CLEARING
CHQ DEBIT`) is locked to the v3.5 C20 cheque-issue keyword list. On
the corpus, UOB's `Chq Wdl NNNNNN` / `Cheque NNNNNNN` shapes are not
matched (Juta Kenangan C20 = 0 rows / RM 0; loose-chq count = 609 /
RM 24.2M). Likewise Hou Tian: C20 = 36 rows / RM 1.6M; loose-chq =
125 rows / RM 1.66M (some overlap with `HOUSE CHQ DR` which IS in
C20). This is a parser-emission concern AND a v3.5 keyword-list gap,
NOT a Track 2 issue. The s12 `CHEQUE_DR_HEURISTIC_RE` (broader,
`\bCHEQUE\b|\bCHQ\b`) deliberately bypasses C20 because it's a
soft-signal heuristic and over-matching small cheque-fee rows is fine
(the absolute-RM gate filters them).

If the dispatcher or future C20 work wants to tighten the gap, it
should extend the C20 keyword list — or document the bank-specific
shapes as a known C20 false-negative class.

### Threshold values are first-cut and corpus-anchored

- **SUBTHRESHOLD_TOTAL_SALARY_RM = 30,000.0** — fits the two FP
  accounts (RE Concept RM 11.8K, Calvin Skin RM 15.25K) and excludes
  all three true-employer accounts. Threshold rationale: RM 30K total
  over a 6-12 month window ≈ RM 2.5-5K / month, which for a single
  payee is either a director's basic or a sole-prop draw, not a true
  employer-of-record relationship.
- **CHANNEL_BLIND_CHEQUE_DR_MIN_RM = 500,000.0** — magnitude floor;
  RE Concept's RM 438K falls below (and is sub-threshold anyway).
- **CHANNEL_BLIND_CHEQUE_DR_MIN_RATIO = 0.10 (10%)** — significance
  gate; ensures cheque-heavy supplier-payment accounts with low
  cheque-share-of-DR don't trip channel-blind by absolute size alone.

All three thresholds are deliberately tunable constants near the top
of the file. If a future calibration run on a larger corpus shows
false positives or negatives, adjust the values and rerun the
statutory tests — no code changes needed.

### Channel-blind reads raw transactions (new reducer kwarg)

`compute_statutory_compliance` now accepts an optional `transactions=`
kwarg. When provided, it calls `compute_channel_blind_indicator`
internally. When omitted, channel-blind defaults to False (neutral
indicator with `is_channel_blind=False`). Backward compatible —
existing callers continue to work; the dispatcher (when it lands)
must pass `transactions=` for the channel-blind branch to activate.

### Sub-threshold reads `monthly_amounts` only

`is_subthreshold_employer` is callable standalone and reads
`salary_paid` from `monthly_amounts`. The reducer calls it
unconditionally (no new kwarg needed). Two parallel helpers with two
different input shapes — kept independent because they are
independent heuristics.

### Parallel-session branch flip — happened once more

Mid-session-12 a docs session committed `480d307 docs: parser audit
v2.1 — fold in auditor pushback on overhead` to the same branch.
Unrelated to Track 2; the three s12 Track 2 commits landed on top
cleanly. This is the sixth recurrence since session 7. Durable
mitigation (`git worktree add ../Bank-Statement-Track2
track-2-development`) declined six times now.

## Cumulative state across sessions 1-12

**Functions ported / built (35 total):**

- s1: `compute_monthly_eod`.
- s2: `compute_risk_flags` + `CANONICAL_FLAGS`.
- s3: `compute_statutory_compliance` (now wired end-to-end through
  s10 + s11; calibrated by s12).
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
- **NEW in s12:** `OWN_ACCOUNT_BLOCK_RE` (extends `is_salary_payment`);
  `SUBTHRESHOLD_TOTAL_SALARY_RM` + `is_subthreshold_employer`;
  `CHANNEL_BLIND_CHEQUE_DR_MIN_RM` + `CHANNEL_BLIND_CHEQUE_DR_MIN_RATIO`
  + `CHEQUE_DR_HEURISTIC_RE` + `compute_channel_blind_indicator`;
  `transactions=` kwarg + `SUB_THRESHOLD` / `CHANNEL_BLIND` overall_status
  branches on `compute_statutory_compliance`; `subthreshold_employer` +
  `channel_blind_employer` indicators on output; Flag 6/7 latent 0%
  fallback bug fix and remark-routing for both indicators.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. The working tree carries uncommitted
modifications and untracked items from **other workstreams**:

- `scripts/sprint6_impact.py`, `scripts/sprint6_raw_gaps.py`,
  `scripts/validate_keywords.py` — modified ~2026-05-07. Unrelated.
- `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`
  — Track 1 frozen file, modified in working tree by a parallel
  session. Not in any Track 2 commit. Flag if it persists.
- Untracked directories under `Bank-Statement/`, `audit_reports/`,
  `bank-statement-analysis-HTML-fresh/`, `validation runs - json/...`,
  plus untracked prompt docs and the verify script
  `scripts/verify_ab_nov.py`.

**Rule:** stage Track 2 work explicitly by path (e.g.
`git add kredit_lab_classify_track2.py tests/<file>`). Never
`git add -A` / `git add .` / `git stash`.

## Open items the user can tackle next

### Recommended first action — Track 2 dispatcher

The dispatcher is now SAFE to stack. The s12 calibration trio
(own-account guard / sub-threshold / channel-blind) removed the
three false-positive bias classes that would have polluted the
dispatcher's input. Net effect: an orchestrator that calls each
`compute_*` in priority order, applies s8/s9 predicates / canonicaliser
/ pairing at the right hooks, and assigns category tags per row, now
inherits a calibrated foundation.

Probably 1-2 sessions. Most of the s8/s9/s10/s11 primitives (ghost
suppression, JomPAY guard, corporate suffix, canonicalisation,
pairing) are still sitting unused waiting for a dispatcher to use them
end-to-end. The new s12 indicators (`subthreshold_employer`,
`channel_blind_employer`) are reducer-output-only — the dispatcher
should NOT re-compute them; it should just pass `transactions=` to
`compute_statutory_compliance` and surface the existing indicators
when rendering Flag 6 / 7 / 8 / 16 remarks.

### Smaller alternative — MYTUTOR-shape business-model signal

Small composition (~1 session) using `COMMISSION_BLOCK_RE` + existing
transfer counting. v3.3.1 `trigger_signal`: "when commission_keyword
count > 20% of individual-transfer DR volume at the pre-analysis
gate, pause and ask the user to confirm employment model." Visible-
impact and isolated. Lower leverage than the dispatcher.

### C20 keyword-list extension (parser-side)

The s12 calibration uncovered that UOB / Maybank parsers emit cheque
withdrawals with shapes (`Chq Wdl NNNNNNN`, `Cheque NNNNNNN`) that
`CHEQUE_ISSUE_RE` deliberately doesn't match. If C20 should match
these (a v3.5 keyword-list decision, not Track 2's call), extend the
list. Otherwise document the gap as a known C20 false-negative class.
Out of scope for Track 2 sessions per the architecture rules; flag to
the user for a parser-track session if it bites.

### Blocked items (unchanged from s11)

- **C01 / C02 own-party** — blocked on BUG-003
  (`normalize_company_suffix` in `core_utils.py`) landing. The s12
  own-account guard (`14baecd`) acts as a partial C05 self-suppressor
  until C01/C02 land; once the dispatcher with name comparison ships,
  it will catch the same shape via name match + counterparty
  canonicalisation, and the C05 guard remains as cheap insurance.
- **C03 / C04 RP detection (RP2/5/6/7/8)** — blocked on RP foundation
  sprint (rebuild RP3 scanner + RP6 constants in Track 2 independently
  of Track 1, then build RP2/5/7/8 from v3.5.6 prompt spec). Allow
  2-3 sessions for the foundation alone.
- **C10 / C11 deterministic** — partly depends on RP foundation.
- **CIMB AI_ASSIST individual salary branch (C05)** — TR TO SAVINGS +
  [name] + salary_keyword. Blocked on SDK integration decision per
  `feedback_no_sdk_until_bank_deploy.md`.

### Sessions 14+

- **`SYSTEM_PROMPT_TRACK2_v0_1.md`** — the thin Tier 4 prompt drafted
  after RP foundation + remaining Tier 2 ports are done.
- **Side-by-side validation gate** — `verify_*_v3a.py` regression suite
  or successor; must pass on all 6 corpora before Track 2 ships.

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline c49b136..HEAD                 # session-12 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 639/639
```

Expected output of the last command:
```
Ran 639 tests in 0.0XXs
OK
```

The `git log` should show **at least** these commits (newest first),
with one unrelated parallel-session commit (`480d307`) interleaved:

```
42d3bfe Track 2 session 12: channel-blind employer branch (Tier 2)
59d804e Track 2 session 12: sub-threshold employer branch + Flag 6/7 0% fix (Tier 2)
14baecd Track 2 session 12: C05 own-account / inter-account guard (Tier 2)
480d307 docs: parser audit v2.1 — fold in auditor pushback on overhead   <- not Track 2
c49b136 prompts: Track 2 session-12 handoff (after session 11)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

Same recurrence pattern. Mid-session-12 `480d307` flipped the branch
under us once; the three s12 commits landed on top cleanly. Sixth
recurrence since session 7.

Durable mitigation:
`git worktree add ../Bank-Statement-Track2 track-2-development`
(creates a sibling physical checkout dedicated to Track 2). User has
declined six times now — only offer again if it bites harder.

## Architecture rules (re-read before any code)

- **Track 1 files frozen indefinitely:**
  - `kredit_lab_classify.py`
  - `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`
    (note: may be modified in the working tree by parallel sessions —
    that modification is NOT staged in any Track 2 commit and should
    remain unstaged)
  - `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`
- Track 2 must NOT import from Track 1 classifier code, and vice versa.
- Parsers and `core_utils` are SHARED infrastructure. Improvements to
  either benefit both tracks — but Track 2 sessions don't *initiate*
  parser/core_utils edits unless the user explicitly approves. C20
  keyword-list extension (above) is exactly this kind of cross-track
  ask.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.
- **Deliberate v3.5 divergences locked through s12:**
  - `COMMISSION_BLOCK_RE` matches plural/past-tense/gerund English
    commission forms (s11). Documented in regex comment.
  - `OWN_ACCOUNT_BLOCK_RE` is a Track 2 extension; not in v3.5 / v3.3.1
    literal text but within the "no employer payroll" spirit (s12).
  - `SUBTHRESHOLD_TOTAL_SALARY_RM` / `CHANNEL_BLIND_*` thresholds are
    Track 2 calibration constants (s12); not in v3.5. Tunable.

## Out of scope for the next session

- Don't edit Track 1 files (see architecture rules).
- Don't run `git add -A` / `git add .` / `git stash` — stage Track 2
  files explicitly by path.
- Don't initiate parser or `core_utils` edits without explicit user
  approval. The C20 keyword-list gap is a candidate but needs ask
  first.
- Don't push to origin without explicit user approval. (User confirmed
  2026-05-11: "no need to push to origin yet". Eight Track 2 commits
  + two handoffs sitting local since.)

## Memory entries that should already be loaded

The user's auto-memory pulls these on session start (verify relevance,
refresh from code if stale):

- `project_track_2_architecture.md` — the 2026-05-01 thin-AI decision.
- `project_track_2_session7_scope.md` — locked session-7 scope and
  memo-literal RP split. **Note:** the queue is now mostly shipped;
  keep the architectural reasoning, ignore the queue.
- `project_track_2_schema_divergence.md` — net_totals schema-vs-Track-1
  divergence; verify pipeline must whitelist.
- `feedback_handoff_vs_architecture.md` — when handoff and memo
  disagree, defer to memo and surface the choice.
- `feedback_track_isolation_design.md` — Track 1 vs Track 2 file
  isolation principle.
- `feedback_no_sdk_until_bank_deploy.md` — file-based handoff to
  claude.ai for now; no SDK integration yet.

A new memory entry would be appropriate for the s12 verdict-taxonomy
expansion (SUB_THRESHOLD / CHANNEL_BLIND) and the threshold constants,
since those are unlikely to be re-derivable from a future cold read of
just the code (the *spirit* and *calibration anchors* matter; the code
shows the *what* but not the *why those specific thresholds*).
Suggested: `project_track_2_statutory_calibration.md`.

If any are missing or seem stale, refresh from the actual code —
memory records are point-in-time snapshots and the truth is in the
repo.

## Suggested first action for the next session

Pick from:

1. **Track 2 dispatcher** — 1-2 sessions. Highest leverage now that
   calibration is complete. Orchestrator that calls each `compute_*`
   in priority order, applies s8/s9 predicates / canonicaliser /
   pairing at the right hooks. Must pass `transactions=` to
   `compute_statutory_compliance` so the channel-blind indicator
   activates. Don't re-compute the s12 indicators — surface them as-is.
2. **MYTUTOR-shape commission-ratio business-model signal** — small,
   isolated, visible-impact (~1 session).
3. **Spot-check 1-2 of the s11 "salary-detected but not on
   CRITICAL" accounts** (the other 15 of the 20 in the s11 Layer-2
   run) — cheap sanity test that the calibration didn't introduce
   *false negatives* (i.e. real CRITICAL gaps that now get
   SUB_THRESHOLD or CHANNEL_BLIND incorrectly). 30 minutes; gates
   whether the threshold values are right.

User's pattern in s8-s12 has been to pick the "low-risk-and-unblocked"
item first. Option 3 (false-negative check) fits that pattern best
and would catch any over-correction in s12's threshold values before
the dispatcher consumes them. Option 1 (dispatcher) is the bigger
leverage and option 2 sits in between.
