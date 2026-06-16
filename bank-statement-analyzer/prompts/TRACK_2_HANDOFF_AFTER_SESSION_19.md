# Track 2 handoff — picking up after session 19

State at end-of-session-19 (2026-05-14). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `2920094`. One Track 2 commit
in session 19 since the s19 handoff (`5d839a1`).

**Test count:** 886 / 886 (was 851 at session 18 end; +35 in s19). Run
`python -m unittest discover tests` to verify.

**One Track 2 commit added in s19 (plus this handoff update):**

| Commit | Function(s) / file | Tests | Role |
|---|---|---|---|
| `2920094` | `LOAN_DISBURSEMENT_RE`; `LOAN_REPAYMENT_RE`; dispatcher C10 (keyword + factoring) rung; dispatcher C11 (keyword + BANK_FEES_RE short-circuit) rung; `DISPATCHER_BLOCKED_CATEGORIES` collapsed to `{C12}` | +35 | RP foundation Slice 3 — C10/C11 dispatcher rungs |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py),
[tests/test_track2_dispatcher.py](../tests/test_track2_dispatcher.py),
[tests/test_track2_orchestrator.py](../tests/test_track2_orchestrator.py).

## What session 19 unblocked

### Slice 3 of RP foundation — C10/C11 dispatcher rungs (`2920094`)

Port of the v3.5 ``classification_order`` C10 and C11 detectors into
the Track 2 dispatcher. The dispatcher is now feature-complete for the
v3.5 priority ladder; only C12 (FD/interest — no detector ported)
remains blocked.

**C10 (loan disbursement / factoring)** fires on CR-side rows via two
routes:

1. Tier-1 keyword regex (`LOAN_DISBURSEMENT_RE`) — v3.5 keyword list:
   LOAN DISB / FINANCING DISB / TRADE FINANCE CR / TRADE FIN / SCF
   TRADE / FACTORING / INVOICE FIN / INVOICE DISCOUNT / BILL PURCHAS /
   BILL DISCOUNT / BANKERS ACCEPTANCE / FACILITY DRAWDOWN.
2. Tier-2 factoring rule — when `factoring_entities` supplies an
   analyst-confirmed entity name and that name appears as a substring
   of either the counterparty bucket OR the description.

Mirrors Track 1's dispatcher rung at L742-745 verbatim: the analyst-
confirmed factoring list is treated as authoritative, so no separate
ADVANCE-keyword gate is applied (Track 2 follows Track 1 over v3.5's
stricter `planworth_rule`).

**C11 (loan repayment)** fires on DR-side rows via the v3.5 LOCKED
regex (`LOAN_REPAYMENT_RE`) — TERM LOAN / LOAN REPAY / FINANCING REPAY
/ MONTHLY INSTALMENT / IB2G DR CA CR LN / TRANSFER TO LOAN / DD CASA
PYMT / FINPAL ISSUER REPAYM — with three priority guards:

* **BANK_FEES_RE short-circuit** — OTHER TRANSFER FEE + Term loan stays
  C24, not C11 (v3.5 line 817). Track 1 absorbs this via the BANK FEES
  bucket firing before description-keyword; Track 2 has no bucket map
  so the `not BANK_FEES_RE.search(...)` guard is inlined at the C11
  rung.
* **Related-party + Instalment → C04 not C11** (v3.5 line 831).
  Naturally satisfied — the C03/C04 rung above runs first.
* **Account-number-only sub-rule** (v3.5 `account_number_only_rule_
  v3_5_3`, e.g. `TRANSFER TO LOAN 12345678L`) → standalone C11.
  Naturally satisfied — the C01/C02 company-root rung cannot match a
  numeric-only description so it falls through to C11.

`LOAN_DISBURSEMENT_RE` and `LOAN_REPAYMENT_RE` live in a new section
between the C20 cheque issue block and the C24 bank fees block. The
dispatcher rung sits between C06-C09 statutory and C13 reversal — the
v3.5 `classification_order` position.

`DISPATCHER_BLOCKED_CATEGORIES` collapses from `{C01-C04, C10-C12}` to
just `{C12}`. RP foundation slices 1-3 (s17-s19) have closed all
non-FD categories.

### Per-corpus loan-section harness deltas with C10/C11 wired

| Corpus | t1 disb | t2 disb | t1 repay | t2 repay | Note |
|---|---|---|---|---|---|
| Maybank Hydrise | 0 | 1 (+1) | 0 | 0 | Track 2 fires C10 on "SCF Trade" RM 1.39M IFS Capital trade-finance proceeds — v3.5 keyword Track 1 has no fallback for |
| Maybank Zaim | 0 | 0 | 0 | 0 | ✓ exact match |
| Upell UOB | 0 | 0 | 0 | 0 | ✓ exact match |
| Juta Kenangan UOB (May) | 0 | 0 | 0 | 0 | ✓ exact match |
| GWE Food Pack UOB | 0 | 0 | 2 | 2 | ✓ exact match |
| UOB Juta Kenangan (Apr) | 0 | 0 | 0 | 0 | ✓ exact match |

**5 of 6 corpora exact loan-section parity.** The 1 deviation is
Track 2 correctly applying v3.5's keyword-fallback spec where Track 1
has a frozen gap.

own_related_transactions deltas from s18 unchanged (-12 Hydrise, -3
Zaim, ±0 elsewhere).

## Critical findings / decisions from session 19

### Track 1 has no C10 keyword fallback

Track 1's `_KEYWORD_RULES` (kredit_lab_classify.py L119-133) covers
C05 / C13-C20 only — no C10 entry. Track 1 fires C10 only via:
(a) `BUCKET_TO_CATEGORY["LOAN DISBURSEMENT"]` (requires parser to
bucket the row), or
(b) `factoring_entities` decisions (analyst-supplied).

Track 2's `LOAN_DISBURSEMENT_RE` covers the v3.5 tier-1 keyword list
verbatim, so it fires on cross-bank descriptions like "SCF Trade" /
"FACTORING" / "INVOICE FIN" that Track 1 misses.

This is the same pattern as s17/s18 — Track 2 follows v3.5; Track 1
has frozen idiosyncrasies. NOT fixing Track 1.

### Hydrise SCF Trade row is a legitimate C10

The single Hydrise C10 fire is:
`CREDIT INWARD RENTAS IFS CAPITAL (MALAYS* R1014002918798 SCF Trade`
— RM 1,393,207.90 from IFS Capital (known supply-chain-finance
provider) on 2025-10-14. `SCF TRADE` is v3.5 C10 tier-1 keyword #5.
Not a false positive — Track 2 correctly applies v3.5 where Track 1
misses it.

### Dispatcher is now feature-complete for v3.5 priority ladder

After Slice 3, every v3.5 `classification_order` category fires in
Track 2 EXCEPT C12 (FD/interest credit). C12 has no Track 2 detector
ported yet — the row falls through to unclassified per v3.5
`no_unknown_bucket`.

The next slice's gate is no longer dispatcher work — it's the Tier 4
system prompt + final validation.

## Sync state vs main

Still 19+ commits behind main. The `app.py` conflict is unchanged.
Defer the merge pending a dedicated sync session.

## Cumulative state across sessions 1-19

**Functions ported / built (77 total, was 75 at s18 end):**

- s1-s18 — see previous handoff for complete list.
- **NEW in s19:**
  - `LOAN_DISBURSEMENT_RE` — v3.5 C10 tier-1 keyword regex.
  - `LOAN_REPAYMENT_RE` — v3.5 C11 LOCKED keyword regex.
  - C10 dispatcher rung (keyword + factoring-entity match).
  - C11 dispatcher rung (keyword + BANK_FEES_RE short-circuit).
  - `DISPATCHER_BLOCKED_CATEGORIES` reduced to `{C12}`.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree still carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path.

## Big-picture progress

19 sessions in. Dispatcher feature-complete for v3.5 priority ladder.
Slices 1-3 of RP foundation all done. **1-3 sessions remaining to
MVP.**

**Remaining to MVP Track 2 (passes side-by-side on 6 corpora):**

| Slice | Sessions | Gates |
|---|---|---|
| `SYSTEM_PROMPT_TRACK2_v0_1.md` draft (Tier 4 prompt) | 1 | Dispatcher done |
| Side-by-side validation gate + corpus runs (6 files) | 0-1 | Harness already exists; run + diff vs tolerance |
| Bug-fix iteration on validation findings | 0-1 | After validation |

**Realistic remaining: 1-3 sessions to MVP.**

(Optional, NOT blocking MVP: C12 FD/interest detector port. Likely a
half-session if a future analyst flags interest-credit misclassifi-
cation. Today the row falls to unclassified, which is conservative.)

## Open items the user can tackle next

### Option 1 — Tier 4 system prompt draft (Recommended)

`prompts/SYSTEM_PROMPT_TRACK2_v0_1.md`. Draft the AI side of the
thin-AI architecture. Tier 4 is the medium-confidence + edge-case
review pass — operates on the deterministic floor's output and either
confirms or routes to MEDIUM for analyst review. Reference the new
RP foundation slices 1-3 deterministic floor.

About 1 session. After this the side-by-side harness can run the
full validation gate.

### Option 2 — Side-by-side validation gate + corpus runs

Already wired (`scripts/track2_side_by_side.py`). Run it on the 6
corpora and write up the tolerances. Should be 0-1 session of mostly
mechanical work — most of the corpora are already at exact parity for
loan/own/RP, so the gate is largely a formality.

### Option 3 — C12 FD/interest detector port

Optional. About 0.5 session. Today the FD/interest credits fall to
unclassified — conservative but a known gap. If analyst feedback on
the 6-corpus run flags it, port the v3.5 C12 keywords + dispatcher
rung.

### Option 4 — Spot-check Hydrise / Zaim director-salary deltas

The -12 / -3 deltas from s18 are still unverified. Worth confirming
those rows are legitimate salary not RP. About 20-30 min.

### Option 5 — Vendor-bucket auto-RP over-fire calibration

The s18 scanner over-fire on vendor-shape labels still stands. NOT
urgent — own-party rungs absorb the most-impactful overlaps.

### Blocked items (updated from s19 outset)

- C12 deterministic FD/interest — no detector ported (lowest priority)
- CIMB AI_ASSIST (Tier 4 prompt territory)
- C01/C02 — **DONE** (s17 marker + s18 company-root)
- C03/C04 — **DONE** (s18 Slice 2 scanner + dispatcher)
- C10/C11 — **DONE** (s19 Slice 3 keyword + factoring)

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 5d839a1..HEAD                 # s19 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 886 / 886
```

Expected output of the last command:
```
Ran 886 tests in 0.0XXs
OK
```

The `git log` should show:

```
<this-handoff-commit> prompts: Track 2 session-20 handoff (after session 19)
2920094 Track 2 session 19: C10/C11 dispatcher rungs (RP foundation Slice 3)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

Optional sanity — re-run the harness on Hydrise to see the single C10
fire this handoff reports:

```bash
python scripts/track2_side_by_side.py "validation runs - json/claude ai prompt file/Full Report Sample (April 2026 - pre-parser-fix baseline)/Full Report Maybank Hydrise Jul25-Dec25.json"
```

You should see `loan_transactions.disbursements count t1=0 t2=1 Δ=+1`
(the SCF Trade fire — expected, see s19 findings above).

## Branch-stability guard

No new occurrences in s19. Seventh recurrence was s13. Durable
mitigation: `git worktree add ../Bank-Statement-Track2
track-2-development`. User has declined seven times now — only offer
again if it bites harder.

## Architecture rules (re-read before any code)

Unchanged from previous handoffs. The s19 slice follows them all:

- Track 1 files frozen indefinitely. (s19 surfaced one more Track 1
  frozen idiosyncrasy — no C10 keyword fallback — not being fixed.)
- Track 2 must NOT import from Track 1. The Slice 3 helpers are
  defined fresh.
- Parsers and `core_utils` are SHARED infrastructure.
- `build_counterparty_ledger` lives in `app.py` — Track 2 consumes its
  output as a kwarg, never imports it.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.

**Deliberate v3.5 divergences locked through s19:**

- `COMMISSION_BLOCK_RE` (s11).
- `OWN_ACCOUNT_BLOCK_RE` (s12).
- `SUBTHRESHOLD_TOTAL_SALARY_RM` / `CHANNEL_BLIND_*` thresholds (s12).
- Dispatcher priority follows v3.5 `classification_order` LITERALLY
  (s13). **C05 salary above C03/C04 RP per spec — Track 1 has them
  reversed.** This produces the Hydrise -12 / Zaim -3 row deltas.
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
- `LOAN_DISBURSEMENT_RE` + `LOAN_REPAYMENT_RE` + C10/C11 dispatcher
  rungs (s19 Slice 3). C10 tier-1 keyword regex is a Track 2-only
  addition — Track 1 has no equivalent keyword fallback and only
  fires C10 via bucket-direct or analyst factoring list. The C11
  BANK_FEES_RE short-circuit is inlined because Track 2 has no
  BUCKET_TO_CATEGORY shortcut.

## Out of scope for the next session

Unchanged from previous handoffs:

- Don't edit Track 1 files. (Especially tempting after the C10
  keyword-fallback finding — DON'T. File as a TODO.)
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Nineteen
  Track 2 commits** + ten handoffs sitting local since 2026-05-11.

## Memory entries that should already be loaded

Unchanged from previous handoff. No new memory entries needed — s19
slice is fully documented in this handoff + the dispatcher docstrings
+ module-level RP foundation comments.

If any seem stale, refresh from the actual code — memory records are
point-in-time snapshots and the truth is in the repo.

## Suggested first action for the next session

Pick from:

1. **Tier 4 system prompt draft** — 1 session. Last big work item;
   dispatcher is done so the prompt can reference the full
   deterministic floor.
2. **Side-by-side validation gate** — 0-1 session. Mechanical run +
   tolerance write-up; mostly already at parity.
3. **C12 FD/interest detector port** — 0.5 session. Optional, fills
   the last priority-ladder gap.

With Slice 3 in, **#1 is the natural continuation**. The Tier 4
prompt closes the architecture and the MVP gate becomes one harness
run away.
