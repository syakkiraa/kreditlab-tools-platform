# Track 2 handoff — picking up after session 21

State at end-of-session-21 (2026-05-14). Use this when starting a
fresh chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `c9c8d30`. One Track 2
commit in session 21 since the s21 handoff (`724e763`).

**Test count:** 890 / 890 (886 + 4 new corpus-gap tests).

**One Track 2 commit added in s21:**

| Commit | Files | Tests | Role |
|---|---|---|---|
| `c9c8d30` | `tests/test_track2_cash_deposits.py`, `tests/test_track2_reversals.py`, `tests/test_track2_statutory_keywords.py` | +4 | Lock 4 new "intentionally_unmatched" corpus gaps surfaced by the side-by-side harness |

No production code touched. Engine + Tier 4 prompt unchanged from s20.

## What session 21 unblocked

### MVP side-by-side validation gate — 6 of 6 corpora passed

Ran `scripts/track2_side_by_side.py` against all 6 verify corpora.
Principal Gas's `full_report.json` was generated this session from
`Bank-Statement/BankIslam/5/*.pdf` via `scripts/verify_bimb_v3a.py`'s
`build_full_report` (saved to `/tmp/track2_s21/principal_gas_full_report.json`).

| Corpus | Path | Result |
|---|---|---|
| Felcra | Bank Rakyat Koperasi Felcra | Aggregates match; 4 real gaps surfaced (cash deposits, inward returns) |
| Mazaa | PBB Mazaa | Aggregates match; only documented deliberate divergences |
| Waja | Waja RHB | Aggregates match; 2 real gaps surfaced (FPX-B2B EPF/LHDN) |
| Mytutor (BIMB) | BIMB Mytutor | Aggregates match; only documented divergences |
| KMZ | BIMB KMZ Jul25-Dec25 | Aggregates match; only documented divergences |
| Principal Gas | BankIslam/5 (parsed in-session) | Aggregates match; documented divergences + 4 T1-side bugs Track 2 actually fixes |

Raw outputs + diffs at `/tmp/track2_s21/{felcra,mazaa,waja,mytutor,kmz,principal_gas}/`
(local-only, not committed).

### Principal Gas — Track 2 corrects 4 Track 1 bugs

Beyond the documented divergences shared with the other corpora,
Principal Gas surfaced four cases where **Track 2 is correct and
Track 1 has a bug**:

1. **closing_balance**: T1=0 (incorrect — T1's `accounts` builder
   reports zero opening AND closing); T2=62,332.79 (matches the
   actual statement-end value, derived correctly from the row trail).
2. **EPF/SOCSO RM 5,700 row tagging**: T1 wrongly tags
   `'KWSP, Socso'` as C06 (EPF) because its regex greedily matches
   bare `KWSP`; T2's regex has `\bKWSP(?=\s|[/\-]|$)` lookahead that
   requires whitespace/slash/hyphen/end-of-string after KWSP. The
   comma after `KWSP` blocks the match, falls through, and
   `\bSOCSO\b` correctly fires C07 instead. v3.5 LOCKED behavior.
3. **Salary detection**: T2 catches `'Net Pay'` (RM 44,770) via
   wider C05 regex; T1's `_KEYWORD_RULES` regex (`BULK SALARY|AUTO
   SALARY|AUTOPAY DR|PAYROLL|GAJI|SALARY|STAFF OVERTIME|...`) does
   NOT include `NET PAY` and misses the row.
4. **monthly_analysis row count**: T1 emits 10 rows for 5 months
   (one zero-row + one real row per month — likely a leftover from
   multi-account scaffolding); T2 emits 5 (one per month), which is
   the correct shape per v6.3.5 schema.

Track 2 is the correct side on all four. No Track-2 bug surfaced on
Principal Gas.

### Cross-corpus parity invariants (every corpus)

These confirm Track 2's plumbing matches Track 1 exactly:

- `top_level_keys`: 15 shared, no t1-only / t2-only.
- `gross_credits`, `gross_debits`, `net_debits`: **exact** match.
- `monthly_analysis` row count: **exact** match.
- `accounts` count: **exact** match.
- `own_related_transactions` count + amount: **exact** match (RP3
  auto-confirm path is symmetric between T1 and T2).
- `loan_transactions.disbursements/repayments`: **exact** match on
  all 5 corpora.

### Deliberate v3.5 divergences (re-confirmed, Track-1-frozen)

Every numerical delta in the consolidated section traces back to one
of these documented intentional differences:

1. **Round-figure CR** — v3.5 LOCKED rule `amount % 10000 == 0`; T1
   frozen on the older `% 1000`. T2 correct. (Felcra -118K, Mazaa
   -57K, Waja -145K, KMZ -61K.)
2. **Own-party side swap → `total_related_party_cr/dr`** — T1 buckets
   own-party CR as RP_cr; T2 buckets as RP_dr. Documented since s15.
   (Every non-Felcra corpus.)
3. **`statutory_compliance` extra keys** — T2 adds
   `channel_blind_employer` + `subthreshold_employer` per s15 schema
   projection. (Every corpus.)
4. **High-value CR — flat-RM100K vs 3×-period-avg** — T1 frozen on
   absolute threshold; T2 implements v3.5 LOCKED relative multiplier.
   (Felcra Δ=-1.13M.)
5. **`unclassified` count: T1 >> T2** — T1 runs headless with default
   `AnalystDecisions` and no AI; T2 runs full deterministic engine.
   The harness docstring explicitly calls this out as the
   "deterministic floor". (Felcra 4358 vs 85, Mytutor 7847 vs 0.)

### Real Track-2 gaps — surfaced and locked

Four bank-specific descriptions match Track 1's `core_utils` wider
regex (`statutory_bucket_for`, `_KEYWORD_RULES`) but NOT Track 2's
v3.5-LOCKED hand-rolled regex:

| Shape | Bank | Affects | Amount |
|---|---|---|---|
| `CASHDEPOSIT` (no CDM, no space) | Bank Rakyat | Felcra cash-deposit flag | RM 5,682.80 (1 row) |
| `IBGINWARDRETURN` (no space) | Bank Rakyat | Felcra inward-return total | RM 3,361.12 (7 rows) |
| `FPX B2B KUMPULAN -` (truncated) | RHB | Waja EPF total | RM 1,068 (2 rows) |
| `FPX B2B LEMBAGA -` (truncated) | RHB | Waja LHDN-tax + flag verdict | RM 11,372 (3 rows) |

s21 locked these as `..._intentionally_unmatched` tests following the
existing precedent at
[test_track2_cash_deposits.py:127](tests/test_track2_cash_deposits.py#L127)
(test_corpus_gap_cdmcashdeposit_no_space_intentionally_unmatched).

**Why not widen the regexes?** That existing test's docstring is
explicit:

> "Track 2 must NOT silently extend coverage — parity with Track 1
> is the side-by-side validation gate. If this test ever flips green,
> it means we drifted: stop and update v3.5 rules first."

The architectural rule is: v3.5 rules file is the source of truth;
Track 2 implements it verbatim. Widening Track 2's regex to catch
these shapes without first updating
`CLASSIFICATION_RULES_v3_5.json` would silently drift the spec.

## Critical findings / decisions from session 21

### MVP gate passed — 6 of 6 corpora

Every numerical delta has been traced to either a documented
deliberate divergence (5 categories above), a corpus shape now
explicitly locked as a gap test (4 shapes), or a Track-1-side bug
that Track 2 actually fixes (4 Principal Gas cases). No unexplained
delta remains. **Track 2 ships.**

### "Intentionally unmatched" is the architecture, not a bug

I initially flagged the 4 shapes above as actionable Track 2 bugs
with a 5-line `\s+` → `\s*` fix. The existing
`test_corpus_gap_cdmcashdeposit_no_space_intentionally_unmatched`
test contradicts that read: per the user's architecture rule, Track
2 must NOT silently extend coverage. The fix path goes through
v3.5 rules first.

Pattern matches `feedback_handoff_vs_architecture` memory: when a
proposed fix conflicts with a ratified architecture rule, surface
the conflict instead of shipping silently.

### Principal Gas full_report generated in-session

Was missing at session start. Reproduced via
`scripts.verify_bimb_v3a.parse_all + build_full_report` against
`Bank-Statement/BankIslam/5/*.pdf` (no password). Result: 176
transactions across 5 files (Aug-Dec 2025), saved to
`/tmp/track2_s21/principal_gas_full_report.json`. If you want it in
the corpora dir, move it to
`validation runs - json/claude ai prompt file/Full Report Sample
(May 2026 - post-parser-fix)/Full Report BIMB Principal Gas.json`
(matches the May post-parser-fix label since it was parsed today
with current parsers).

## Sync state vs main

Still 19+ commits behind main. Unchanged. Defer.

## Cumulative state across sessions 1-21

**Functions ported / built (77 total, unchanged from s19/s20):**

s21 added no Python functions — only 4 unit tests asserting that
the v3.5 LOCKED regex does NOT match the 4 corpus shapes above.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree still carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path.

## Big-picture progress

21 sessions in. Engine feature-complete; Tier 4 prompt drafted;
side-by-side validation gate **passed for all 6 of 6 corpora** with
every delta traced. **MVP ship verdict: GO.**

**Remaining to first analyst trial:**

| Slice | Sessions | Gates |
|---|---|---|
| App.py wire-through (config flag to route to Track 2) | 1 | Optional but unblocks Streamlit trial |
| claude.ai end-to-end smoke with Tier 4 prompt | 0 (~30 min) | Real-world prompt validation |

**Realistic remaining: 0-1 sessions to first analyst trial.** Ship
verdict is met; the remaining work is integration, not validation.

(Optional, NOT blocking MVP ship:
* v3.5 rules update for the 4 corpus shapes locked in s21, then
  re-sync Track 2 regexes. Closes the residual numerical gaps.
* C12 FD/interest detector port (engine).
* v0.2 prompt trim + MEDIUM-RP reclass step.
* Streamlit / app.py wire-through to actually use Track 2 end-to-end.)

## Open items the user can tackle next

(MVP gate already passed — these are post-ship work.)

### Option 1 — End-to-end smoke through claude.ai (Recommended)

Take any of the 6 engine outputs (paste into a fresh claude.ai
session with `SYSTEM_PROMPT_TRACK2_v0_1.md` + filled
`RUN_INPUT_TEMPLATE.md`) and confirm the analyst-side ergonomics
work. First real-world Tier 4 prompt test. About 30 min. Highest
ROI for the next session — it surfaces the prompt's actual usability
before you scale up to real analyst trials.

### Option 2 — App.py Track 2 wire-through

Add a config flag (`USE_TRACK_2=true` env var or sidebar toggle) to
let runs pick Track 1 or Track 2 from the Streamlit UI. About 1
session; this is what unblocks the first internal analyst trial of
the full pipeline.

### Option 3 — v3.5 rules update for the 4 locked corpus gaps

Edit `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`:

* C17 (cash deposits) regex: add `CASHDEPOSIT` (no space) and confirm
  the LOCKED rule against parser test corpora.
* C16 (IBG/GIRO inward return) regex: allow `\\s*` instead of `\\s+`
  between IBG / GIRO / INWARD / RETURN tokens.
* C06 (KWSP/EPF) regex: add `FPX\\s*B2B\\s+KUMPULAN(?=\\s|$|/|-)`.
* C08 (LHDN tax) regex: add `FPX\\s*B2B\\s+LEMBAGA(?=\\s|$|/|-)`.

Then re-sync Track 2's `CASH_DEPOSIT_RE`, `INWARD_RETURN_RE`,
`EPF_PAYMENT_RE`, `LHDN_TAX_PAYMENT_RE`. The 4 s21 gap tests will
flip to assert the NEW (passing) behavior — read them as the
gap-closure spec when you do this. About 0.5-1 session including
cross-bank regression.

### Blocked items (updated end-of-s21)

- C12 deterministic FD/interest — no detector ported (lowest priority).
- CIMB AI_ASSIST — Tier 4 prompt territory; covered generically in
  v0.1 draft.
- Principal Gas — **DONE** (full_report generated + side-by-side
  passed in s21).

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline c9c8d30..HEAD                 # s21 endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 890 / 890
```

Expected output of the last command:
```
Ran 890 tests in 0.0XXs
OK
```

The `git log` should show:

```
<this-handoff-commit> prompts: Track 2 session-22 handoff (after session 21)
c9c8d30 Track 2 session 21: 4 corpus-gap tests from side-by-side validation
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

Optional sanity — re-run the side-by-side on Felcra to see the
locked-gap diffs:

```bash
python scripts/track2_side_by_side.py "validation runs - json/claude ai prompt file/Full Report Sample (April 2026 - pre-parser-fix baseline)/Full Report Bank Rakyat Koperasi Felcra.json"
```

Expected gaps (now locked as tests):
- `total_cash_deposits` t1=5,982.80 t2=0
- `total_inward_return_cr` t1=3,361.12 t2=0
- `Cash Deposits (AML)` flag verdict: t1=detected t2=not-detected

## Branch-stability guard

No new occurrences in s21. Seventh recurrence was s13. Durable
mitigation: `git worktree add ../Bank-Statement-Track2
track-2-development`. User has declined seven times — only offer
again if it bites harder.

## Architecture rules (re-read before any code)

Unchanged from previous handoffs. The s21 test-only commit follows
them all. **One rule worth re-stating after s21:**

- Track 2 implements `CLASSIFICATION_RULES_v3_5.json` regex
  **verbatim**. When the parser emits a bank-specific shape that
  the LOCKED rule doesn't cover, lock it as a corpus-gap test —
  do NOT widen the Track 2 regex without updating v3.5 first. The
  side-by-side gate is parity-with-v3.5, not parity-with-T1.
  ([test_track2_cash_deposits.py:118-121](tests/test_track2_cash_deposits.py#L118-L121))

**Deliberate v3.5 divergences locked through s21:**

(Unchanged from s20 handoff — no new divergences added in s21. The
4 s21 gap tests are NOT divergences; they're spec-gap markers
waiting for a v3.5 rules update.)

## Out of scope for the next session

Unchanged from previous handoffs:

- Don't edit Track 1 files.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Twenty-one
  Track 2 commits** + twelve handoffs sitting local since 2026-05-11.
- Don't widen `CASH_DEPOSIT_RE`, `INWARD_RETURN_RE`, `EPF_PAYMENT_RE`,
  or `LHDN_TAX_PAYMENT_RE` in Track 2. v3.5 rules update first
  (see Option 3 above).

## Memory entries that should already be loaded

Unchanged from previous handoff. No new memory entries needed — s21
is fully captured in this handoff + the 4 test docstrings.

If any seem stale, refresh from the actual code — memory records
are point-in-time snapshots.

## Suggested first action for the next session

Pick from:

1. **claude.ai smoke** — 30 min. First real-world Tier 4 prompt
   test; surfaces analyst-side ergonomic issues before scaling up.
2. **App.py wire-through** — 1 session. Lets analysts actually run
   Track 2 from the Streamlit UI; unblocks first internal trial.
3. **v3.5 rules update for the 4 locked gaps** — 0.5-1 session.
   Closes the residual side-by-side numerical gaps; not blocking
   ship.

With the 6-of-6 MVP gate passed in s21, **#1 is the highest ROI**.
The validation work is done; from here it's integration + first
analyst contact.
