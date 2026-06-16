# Track 2 handoff — picking up after session 11

State at end-of-session-11 (2026-05-12). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `4ca35d4`. Four Track 2
commits across sessions 10 and 11 since the previous handoff
(`1fd9212`). Also picked up two unrelated parallel-session commits
between them (`51c2a1d fix(app): preserve (MAYBANK in counterparty
normalisation` and `86786e0 docs: rewrite parser quality audit prompt
+ HUAHUB session handoff`) — both unrelated to Track 2; leave alone.

**Test count:** 594 / 594 (was 431 at session 10 start; +163 across two
sessions over four commits). Run `python -m unittest discover tests`
to verify.

**Four Track 2 commits added since the s9 handoff:**

| Commit | Function(s) | Tests | Role |
|---|---|---|---|
| `fabd12f` | `compute_epf_payments` / `compute_socso_payments` / `compute_lhdn_tax_payments` / `compute_hrdf_payments` | 49 | C06-C09 per-row keyword detectors (s10) |
| `2066d7c` | `compute_statutory_monthly_amounts` | 27 | Bridges the four C0x detectors -> existing `compute_statutory_compliance` (s3) (s10) |
| `77a3823` | `compute_unkeyworded_return_pair_count` + new `unkeyworded_return_pair_count` kwarg on `compute_data_completeness` | 16 | Flag 13 Data Quality wiring — composes s9 `pair_ibg_duitnow_returns` with s7 C16 keyword (s10) |
| `4ca35d4` | `SALARY_KEYWORD_RE` / `COMMISSION_BLOCK_RE` / `is_salary_payment` / `compute_salary_payments` | 71 | C05 salary / payroll detector — activates Flags 6/7 (s11) |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); new
test files under `tests/test_track2_*.py` — one per commit.

## What sessions 10-11 unblocked

**The statutory chain is now end-to-end deterministic and producing
realistic verdicts on real corpus** — this is the big change vs s9.
Before sessions 10/11, the chain stopped at the s3 reducer's salary-
empty branch (always COMPLIANT, Flags 6/7 dark). After s11, the full
pipeline runs:

```
transactions
  ├─→ compute_salary_payments       ─┐
  ├─→ compute_epf_payments          ─┤
  ├─→ compute_socso_payments        ─┼─→ compute_statutory_monthly_amounts ─→ compute_statutory_compliance ─→ Flags 6/7/8/16
  ├─→ compute_lhdn_tax_payments     ─┤
  └─→ compute_hrdf_payments         ─┘

transactions ─→ pair_ibg_duitnow_returns ─→ compute_unkeyworded_return_pair_count
                                                          │
                                                          ▼
            compute_data_completeness(monthly_reconciliation, unkeyworded_return_pair_count=...) ─→ Flag 13
```

**Flag coverage:** 12/16 -> 13/16 effective. Flags 6 (EPF), 7 (SOCSO),
13 (Data Quality) now produce real verdicts. Flag 8 (LHDN) and Flag 16
(HRDF) are presence-only and were already counted in s9's tally.

## Critical findings / decisions from sessions 10-11

### Salary-chain verdict calibration — UNRESOLVED, FIRST PRIORITY

The Layer-2 corpus run for s11 surfaced **five CRITICAL verdicts** out
of 20 statements where salary was detected: Hou Tian (MBB) / Juta
Kenangan (UOB) / HLB MTCE / RE Concept (Ambank) / Calvin Skin (OCBC).
All show 0% EPF coverage despite active salary months.

**These could be either:**
- Real compliance gaps the analyst wants surfaced (correct CRITICAL).
- Sole-prop / sub-threshold employers paying salary without statutory
  obligation (false-positive CRITICAL — v3.3.1's
  `impact_expectation` for commission businesses applies here too).

**Until we ground-truth at least one or two of these, every downstream
consumer inherits a potential false-positive bias.** Twenty minutes of
eyeballing one CRITICAL statement (matched against its real PDF +
parser output) tells us whether the chain is calibrated or whether the
v3.3.1 "no payroll obligation" spirit needs to extend to a no-EPF-
because-sole-prop branch.

### GAJI word-boundary guard — locked

`\bGAJI\s+(?:BULANAN|BLN|JAN|...)\b` rejects MENGAJI / NGAJI tuition-
business substring collisions. Plain `\bGAJI\b` would over-match on
education / tutoring shapes (the v3.5 `salary_regex_note` is the
written-down rule, locked here by the GajiBoundaryGuardTests).

### Commission policy extended beyond v3.5 list (per user 2026-05-12)

v3.3.1 lists nine commission keywords (COMM / COMMS / COMMISSION /
COMMISION / PT COMM / PT COMMS / KOMISEN / KOMISYEN / HABUAN). User
asked explicitly for the English equivalent of KOMISYEN to be
complete — extended `\bCOMMIS(?:S)?ION\b` to
`\bCOMMIS(?:S)?ION(?:S|ED|ING)?\b` so COMMISSIONS / COMMISIONS /
COMMISSIONED / COMMISSIONING also block. **This is a deliberate
extension beyond what v3.5 lists literally — documented in the regex
comment as "within the v3.3.1 policy's intent".** If the v3.5 rules
file is ever re-extracted from claude.ai for parity comparison, this
divergence is intentional.

### MYTUTOR distortion fix — confirmed working on corpus

s11 corpus run: MYTUTOR has 6,550 rows with a commission keyword. ALL
6,550 are blocked from C05 by `COMMISSION_BLOCK_RE`. Detector still
hits 24 legitimate salary rows (`TRANSFER FR A/C ... * Salary` shape)
without inflation from tutor "Comm PT" payments. The v3.3.1 policy
distortion fix works as documented.

### Flag 13 has expected false-positive rate from structural-only pairing

s9's `pair_ibg_duitnow_returns` has no CR-side keyword filter —
pairing is purely structural on amount + same-or-after date within the
business-day window. On corpus, Flag 13 fires 42 times across 6 files,
mixing genuine extraction gaps (Plentitude `DuitNow TRF /MISC CREDIT,
BOND MOBILE SOLUTION, refund, IBG` — clear refund whose keyword "refund"
isn't in the LOCKED C16 regex which only matches "IBG INWARD RETURN" /
"GIRO INWARD RETURN") with legitimate same-amount same-day inter-
account round-trip business activity (UOB GWE Food Pack BORE / GOODWILL
EVEREST flows). **Documented behaviour** — Flag 13 is an attention
signal, not a hard "C16 was missed" assertion. Tightening (CR-side
keyword gate, RP/own-party exclusion) is a deliberate change to s9 +
s10 that would need explicit scope.

### Parallel-session branch flip — happened twice more

Mid-session-10 a parser-fix session (`51c2a1d`) and mid-session-11 a
docs session (`86786e0`) committed to the same branch. Both are
unrelated to Track 2 and my commits landed on top cleanly each time.
This is the fifth recurrence since session 7. User has consistently
declined the `git worktree add ../Bank-Statement-Track2
track-2-development` mitigation. Offer again if it bites harder.

## Cumulative state across sessions 1-11

**Functions ported / built (30 total):**

- s1: `compute_monthly_eod`.
- s2: `compute_risk_flags` + `CANONICAL_FLAGS`.
- s3: `compute_statutory_compliance` (now actually wired through s10+s11).
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
- **NEW in s10:** `compute_epf_payments` / `compute_socso_payments` /
  `compute_lhdn_tax_payments` / `compute_hrdf_payments` (C06-C09);
  `compute_statutory_monthly_amounts` (aggregator);
  `compute_unkeyworded_return_pair_count` + new
  `unkeyworded_return_pair_count` kwarg on `compute_data_completeness`
  (Flag 13 wiring).
- **NEW in s11:** `SALARY_KEYWORD_RE`, `COMMISSION_BLOCK_RE`,
  `is_salary_payment`, `compute_salary_payments` (C05).

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. The working tree carries uncommitted
modifications and untracked items from **other workstreams**:

- `scripts/sprint6_impact.py`, `scripts/sprint6_raw_gaps.py`,
  `scripts/validate_keywords.py` — modified ~2026-05-07, predate the
  parser-hlb branch's HLB commit by a day. Unrelated to Track 2.
- A NEW dirty file appeared during sessions 10/11: `validation runs -
  json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`. **That is a
  Track 1 frozen file per the architecture rules** — its working-tree
  modification came from a parallel session. Not staged, not in any
  Track 2 commit. Flag this to the user if it persists; otherwise
  leave alone.
- Untracked directories under `Bank-Statement/`, `audit_reports/`,
  `bank-statement-analysis-HTML-fresh/`, `validation runs - json/...`,
  plus untracked prompt docs and the verify script
  `scripts/verify_ab_nov.py`.

**Rule:** stage Track 2 work explicitly by path (e.g.
`git add kredit_lab_classify_track2.py tests/<file>`). Never
`git add -A` / `git add .` / `git stash`.

## Open items the user can tackle next

### Recommended first action — calibrate before building more

**Spot-check the five CRITICAL verdicts** (Hou Tian / Juta Kenangan /
HLB MTCE / RE Concept / Calvin Skin). Read one or two of the actual
PDFs alongside the parser output. If the verdict matches a real
compliance gap, the chain is calibrated; if the account is a sole-
prop / sub-threshold employer where 0% EPF is correct, the v3.3.1
"no payroll obligation" spirit needs a sole-prop branch in the s3
reducer or in C05 itself.

Cheap to do (~20 minutes). Prevents stacking a dispatcher on top of a
potentially mis-calibrated foundation.

### Larger Tier 2 work — biggest single unblock

- **Track 2 dispatcher** — orchestrator that calls each `compute_*` in
  priority order, applies the s8/s9 predicates / canonicaliser /
  pairing at the right hooks, and assigns category tags per row.
  Single biggest unblocked item. Probably 1-2 sessions. Most of the
  s8/s9/s10/s11 primitives (ghost suppression, JomPAY guard, corporate
  suffix, canonicalisation, pairing) are sitting unused waiting for a
  dispatcher to use them end-to-end.

### Compositions that the s10/s11 work unlocked

- **Flag 6/7 reducer downstream consumers** — if anything else in
  Track 2 reads compliance verdicts, it now reads real ones, not
  always-COMPLIANT placeholders.
- **MYTUTOR-shape detection in business-model observations** — when
  COMMISSION_BLOCK_RE fires often enough that legitimate salary count
  is near zero on an account, surface that as a business-model signal
  (commission agency / freelance platform / MLM) in observations.
  v3.3.1 `trigger_signal` says "when commission_keyword count > 20%
  of individual-transfer DR volume at the pre-analysis gate, pause and
  ask the user to confirm employment model" — Track 2 could compute
  this ratio and emit it.

### Blocked items (unchanged from s9)

- **C01 / C02 own-party** — blocked on BUG-003
  (`normalize_company_suffix` in `core_utils.py`) landing.
- **C03 / C04 RP detection (RP2/5/6/7/8)** — blocked on RP foundation
  sprint (rebuild RP3 scanner + RP6 constants in Track 2 independently
  of Track 1, then build RP2/5/7/8 from v3.5.6 prompt spec). Allow 2-3
  sessions for the foundation alone.
- **C10 / C11 deterministic** — partly depends on RP foundation.
- **CIMB AI_ASSIST individual salary branch (C05)** — TR TO SAVINGS +
  [name] + salary_keyword. When the row has no salary keyword in the
  bank-emitted description, only AI scoring against the extracted
  counterparty name can decide. Blocked on SDK integration decision
  per `feedback_no_sdk_until_bank_deploy.md`.

### Sessions 13+

- **`SYSTEM_PROMPT_TRACK2_v0_1.md`** — the thin Tier 4 prompt drafted
  after RP foundation + remaining Tier 2 ports are done.
- **Side-by-side validation gate** — `verify_*_v3a.py` regression suite
  or successor; must pass on all 6 corpora before Track 2 ships.

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 1fd9212..HEAD                 # session-9 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 594/594
```

Expected output of the last command:
```
Ran 594 tests in 0.0XXs
OK
```

The `git log` should show **at least** these commits (newest first),
with two unrelated parallel-session commits (`51c2a1d`, `86786e0`)
interleaved among the Track 2 work:

```
4ca35d4 Track 2 session 11: C05 salary / payroll detector (Tier 2)
86786e0 docs: rewrite parser quality audit prompt + HUAHUB session handoff   <- not Track 2
77a3823 Track 2 session 10: Flag 13 Data Quality wiring (Tier 2)
2066d7c Track 2 session 10: statutory monthly aggregator (Tier 2)
51c2a1d fix(app): preserve `(MAYBANK` in counterparty normalisation         <- not Track 2
fabd12f Track 2 session 10: C06-C09 statutory keyword detectors (Tier 2)
1fd9212 prompts: Track 2 session-10 handoff (after session 9)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

Unchanged in essence — the recurrence rate is the news. There is only
one physical worktree at this directory. Parallel Claude sessions
running `git checkout` flip this session's branch under it. Happened
in session 8, session 9, session 10 (twice — `51c2a1d` and the brief
mid-session checkout-to-main), and session 11 (`86786e0`).

Durable mitigation:
`git worktree add ../Bank-Statement-Track2 track-2-development`
(creates a sibling physical checkout dedicated to Track 2). User has
declined this five times now — offer once more if the issue causes a
real problem (e.g., a Track 2 commit ends up on the wrong base).

## Architecture rules (re-read before any code)

- **Track 1 files frozen indefinitely:**
  - `kredit_lab_classify.py`
  - `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`
    (note: this file was modified in the working tree mid-s10/s11 by a
    parallel session — that modification is NOT staged in any Track 2
    commit and should remain unstaged)
  - `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`
- Track 2 must NOT import from Track 1 classifier code, and vice versa.
- Parsers and `core_utils` are SHARED infrastructure. Improvements to
  either benefit both tracks — but Track 2 sessions don't *initiate*
  parser/core_utils edits unless the user explicitly approves.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.
- **Deliberate v3.5 divergence locked in s11:** `COMMISSION_BLOCK_RE`
  matches the plural/past-tense/gerund English commission forms that
  v3.3.1 doesn't list literally. Documented in the regex comment.

## Out of scope for the next session

- Don't edit Track 1 files (see architecture rules).
- Don't run `git add -A` / `git add .` / `git stash` — stage Track 2
  files explicitly by path.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't push to origin without explicit user approval. (User confirmed
  2026-05-11: "no need to push to origin yet". Five Track 2 commits
  + this handoff are sitting local since.)

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

If any are missing or seem stale, refresh from the actual code — memory
records are point-in-time snapshots and the truth is in the repo.

## Suggested first action for the next session

Pick from:

1. **Calibrate the statutory chain** — spot-check 1-2 of the five
   CRITICAL verdicts (Hou Tian / Juta Kenangan / HLB MTCE / RE Concept
   / Calvin Skin) against their actual PDFs. Cheapest item, biggest
   information value, gates whether Flags 6/7 are usable downstream.
2. **Track 2 dispatcher** — 1-2 sessions. Highest leverage if calibration
   step passes. Puts the s8/s9/s10/s11 primitives to actual use.
3. **MYTUTOR-shape commission-ratio business-model signal** — small
   composition using `COMMISSION_BLOCK_RE` + existing transfer
   counting. Visible-impact and isolated.

The user's pattern in s8-s11 has been to pick the "low-risk-and-
unblocked" item first. Option 1 (calibrate) fits that pattern best.
The dispatcher is bigger and waits well on the calibration outcome.
Ask before starting if scope is unclear.
