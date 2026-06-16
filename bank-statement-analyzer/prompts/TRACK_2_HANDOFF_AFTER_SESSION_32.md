# Track 2 handoff — picking up after session 32

State at end-of-session-32 (2026-05-22). Two ship-ready items closed
hard this session — renderer is now live on its remote `main`, and
the Bank Rakyat residuals triage produced a real Track 2 engine fix
that's local on `track-2-development`. With the s32 scope reset (no
keyword loop, no Affin, no SDK), **engine-side ship-ready is
effectively done** modulo one optional follow-up (BR/8 utility
cluster) and the push of the local engine commit.

**Read first:**
1. `~/.claude/projects/.../memory/project_ship_ready_strategy.md` —
   **UPDATED s32 footer.** Three items closed (renderer pushed,
   keyword loop cancelled with reason, BR triage shipped). New punch
   list at bottom is short: push `86f710d` + optional BR/8 utility
   cluster + auth.
2. `~/.claude/projects/.../memory/project_html_renderer_version_gap.md` —
   **UPDATED s32 footer.** Renderer is on `origin/main` at `652099a`;
   `renderer-v6.3.5-support` branch is now redundant.
3. `~/.claude/projects/.../memory/project_track_2_architecture.md` —
   the architecture rule that drove the s32 keyword-loop cancellation
   decision (engine-heavy, thin AI; rules JSON is reference for
   narrative, not classification source).
4. `~/.claude/projects/.../memory/feedback_renderer_vs_classifier.md` —
   standing rule. Renderer is now in sync with engine; don't fix
   classification issues in the renderer.
5. `~/.claude/projects/.../memory/feedback_source_file_ceiling.md` +
   `feedback_audit_claude_misdiagnosis.md` — the rules that drove
   the s32 BR/8 fix to be verified against raw PDF text before any
   engine edit and re-verified after the first version exposed a
   2,253-row companion-fee-row FP that was caught and fixed before
   commit.
6. `prompts/TRACK_2_HANDOFF_AFTER_SESSION_31.md` — predecessor.

## What landed in s32

Two repos touched. Renderer change pushed to origin; engine change
local-only.

| # | Commit | Repo / branch | Effect |
|---|---|---|---|
| 1 | `652099a` (merged + pushed) | renderer `main` on `github.com/luqman196/bank-statement-analysis-HTML` | s31's three renderer additions (subthreshold + channel-blind + extraction_stats cards) merged fast-forward into renderer `main` and pushed to origin. Renderer hosting (Procfile present, hosting status unverified) may have auto-deployed. Track 1 byte-identical preserved per `acd6112` contract. |
| 2 | `86f710d` (local only) | parser `track-2-development` | **Track 2 engine: concat-form salary regex + companion-fee-row block.** Two paired changes in `kredit_lab_classify_track2.py`. (a) `_SALARY_KEYWORD_CONCAT_RE` catches Bank Rakyat DATAPOS concat shapes — `GAJI<MONTH>[YYYY]` (BM + English month names, full + abbrev) and `STAFFID<NNN>`. Bounded FP surface via `(?<![A-Z])` lookbehind + strict month alternation + `\\d+` requirement. Mirrors s30 `_CORPORATE_SUFFIX_CONCAT_RE` pattern. (b) `_BANK_FEE_BLOCK_RE` blocks companion fee rows (CIBSMSFEE / CIBDRCHARGES / DUITNOWFEE / IBGFEE / SMSFEE) — the BR parser concatenates the underlying salary's metadata onto the RM 0.10 / RM 0.50 fee row, so without this block the new regex tagged 2,253 fee rows as C05. Generic `\\bFEE\\b` deliberately avoided. +20 tests in `test_track2_salary.py` (15 concat positive/guard + 5 fee-block). |

**Bank Rakyat triage results (closes s31 punch list item):**
- BR/1 (Cash Line, CENFOTEC SDN BHD, 15 tx): **100% classified, 0
  unclassified.** No work needed — spot-check complete.
- BR/7 (s30 baseline, KOPERASIFELCRA, 577 tx): **86.8% → 90.3%**
  (76 → 56 unclassified, −20 rows). C05 went 0 → 20.
- BR/8 (never measured at s30, KOPERASIFELCRA different account,
  4,373 tx): **59.8% → 90.1%** (1,758 → 434 unclassified, −1,324
  rows). C05 = 1,341 (matches independent heuristic estimate 1,339).
  C24 stable at 2,482 — fee rows correctly remain in C24, not
  poached.

**Discrepancy resolved:** s30 handoff said "76 unclassified on
Felcra" — that number was correct **for BR/7** (the corpus s30
actually measured). BR/8 is a different Felcra account, larger and
unaddressed at s30. Both folders show company `KOPERASIKAKITANGANFELCRA(M)BERHAD`
but the filename suffix pattern + transaction count differ.

**Tests:** 1040 → 1060 (+20, all green). Track 1 regression 6/6
green in 73s (no Track 1 bleed — change is Track-2-only).

**Memory updates this session:**
- `project_ship_ready_strategy.md` — s32 footer: three items closed
  + new short punch list + remaining-sessions estimate dropped to
  0-1
- `project_html_renderer_version_gap.md` — renderer pushed to
  origin; branch now redundant

## Where we are on the ship-ready line

**Pre-s32 estimate:** ~1-3 sessions remaining in scope.
**Post-s32:** **0-1 sessions** remaining + push gate + auth scope
decision (separate).

**In-scope ship-ready punch list (very short now):**

| Item | Sessions | Status |
|---|---|---|
| Push `86f710d` to `origin/track-2-development` | ~0.1 | gated on user explicit "push" instruction |
| BR/8 residual cluster: `CIBDRADVICE(JomPA` utilities (91 rows: DIGI/TNB/water/TM/sewage) | 0-1 | optional follow-up; extractable Bank-Rakyat-specific JomPay channel pattern. Not on s31 punch list; treat as bonus engine work, not ship-ready blocker |
| Auth / multi-tenant | TBD | gated by undecided selling-motion |

**Explicitly OUT of ship-ready scope (carried forward, unchanged):**

| Item | Re-trigger |
|---|---|
| Affin OCR | user explicit unblock + tesseract install OR Railway prod sample (see `project_affin_ocr_deferred.md`) |
| V3-B Auto-RP Step 2 SDK | user explicit unblock + claude.ai web workflow stable (see `feedback_no_sdk_until_bank_deploy.md`) |
| Keyword loop CP1–CP11 | **promoted to out-of-scope in s32** — doesn't benefit Track 2 (engine-heavy architecture; rules JSON is narrative-only for Track 2 per `SYSTEM_PROMPT_TRACK2_v0_1.md` trust order). Re-trigger only if user shifts focus back to Track 1 / claude.ai web flow. |

**Items already closed (cumulative through s32):**
- ~~#2 Cheap classifier wins~~ (s30, commits `cce8e61` + `7fde7c2`)
- ~~#3 Bank Rakyat DATAPOS edge cases~~ (s30 `7fde7c2`)
- ~~#4 Regression suite~~ (s29, commit `1cdfe82`)
- ~~#5 Mytutor per-business-type rule~~ (s30, verified ceiling)
- ~~Renderer schema sync v6.3.3 → v6.3.5~~ (s31 `652099a`; s32 merged
  to main + pushed)
- ~~BR residuals + Cash Line triage~~ (s32 `86f710d` — BR/7 closed,
  BR/8 substantially closed, BR/1 confirmed no-op)
- ~~Keyword loop CP1-CP11~~ (s32 cancelled with reason — not a
  Track 2 ship-ready item)

## Out-of-scope (unchanged + s32 additions)

Standing rules carried forward:
- Don't edit Track 1 files (`kredit_lab_classify.py`, `app.py` in repo
  root, `SYSTEM_PROMPT_v3_5_6.md`) without explicit user approval.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser or renderer) without explicit user
  approval. (Renderer was pushed in s32 with explicit user approval;
  the same gate applies to the engine commit `86f710d` going forward.)
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the `main` → `track-2-development` merge unless
  explicitly scoped as a sync session.
- Don't fix classification/analysis issues in the renderer
  (`feedback_renderer_vs_classifier.md`).
- Before acting on any quality-report / audit / "missed keywords"
  finding, verify against raw PDF text first per
  `feedback_source_file_ceiling.md`. Source-file ceilings are not
  bugs to fix.
- Don't start Affin OCR work without the gate in
  `project_affin_ocr_deferred.md` being satisfied.
- Affin OCR is OUT of ship-ready scope per s31; don't surface it.
- V3-B Auto-RP Step 2 SDK is OUT of ship-ready scope per s31; don't
  surface it.

**NEW s32 (scope discipline):**
- **Keyword loop CP1-CP11 is OUT of ship-ready scope** as a Track 2
  effort. The Track 2 architecture (`SYSTEM_PROMPT_TRACK2_v0_1.md`
  trust order) treats the rules JSON as narrative reference, not
  classification source — engine code in `kredit_lab_classify_track2.py`
  is the source of truth. Improving CP1-CP11 only helps the Track 1
  claude.ai web flow. Re-trigger only if user explicitly shifts back
  to Track 1 priorities.
- **Track 2 engine fixes for surfaced bank patterns are in scope**
  and welcomed, as demonstrated by s32 `86f710d`. Workflow:
  inspection script → raw-PDF verification → bounded-FP regex
  design → +tests → run full suite + regression → re-measure →
  commit. The s32 fix showed why measurement-after-implementation
  matters: first version had a 2,253-row companion-fee FP that was
  caught and fixed before commit.

## First commands the next session should run

```bash
git status --short                                              # confirm known-dirty matches state
git branch --show-current                                       # MUST be track-2-development
git log --oneline 3acd5cf..HEAD | head                          # should show 86f710d at top + 13ba231 + 621b57b + 7fde7c2 + cce8e61
python -m unittest discover tests 2>&1 | tail -5                # confirm 1060 / 1060 (6 skipped)
RUN_REGRESSION=1 python -m unittest tests.regression.test_snapshots 2>&1 | tail -3  # optional: 6/6 green (~73s)
git -C bank-statement-analysis-HTML-fresh branch --show-current # main (renderer-v6.3.5-support is now redundant)
git -C bank-statement-analysis-HTML-fresh log -1 --oneline      # 652099a on main
git -C bank-statement-analysis-HTML-fresh log origin/main..main --oneline  # should be EMPTY (pushed)
```

If any don't match → stop and investigate.

## Suggested first action for the next session

The session should branch based on what the user wants next:

### Path A — push `86f710d` to origin

If user instructs "push", run:
```bash
git push origin track-2-development
```
Then verify with `git log origin/track-2-development..track-2-development --oneline` (should be empty).

This is the cleanest close-out of the s32 work. Single command, low
risk, no test runs needed (already validated).

### Path B — BR/8 utility-cluster engine fix

The 91 `CIBDRADVICE(JomPA` rows (DIGI 45, TNB 19, water 15, Indah
Water 7, TM 5) are a Bank-Rakyat-specific JomPay channel pattern
that's mechanically extractable. Pattern shape:
`94804 CIBDRADVICE(JomPA <amount> <UTILITY-MERCHANT-NAME> <ref>`

Approach (same workflow as s32):
1. Open one BR/8 PDF; grep for `CIBDRADVICE(JomPA` to confirm raw
   text matches what the parser emits.
2. Check what bucket/category the engine currently routes these to
   (probably UNCLASSIFIED on CR side, or C24 fees if any).
3. Decide the target category. Utility payments are usually C26
   (supplier expense) but each merchant name needs verification —
   DIGI/TNB/water utilities are C26-supplier shapes; some JomPay
   payments are to merchants (Coway, etc.) which may be C24/C26.
4. Design a bounded regex or extend an existing utility/merchant
   detector. Per s32 hindsight, verify cross-bank doesn't false-
   positive on non-BR statements.
5. +tests, full suite, regression, measurement.

This is a real Track 2 engine improvement but **not a ship-ready
blocker** — the s32 fix already moved BR/8 from 59.8% to 90.1%, and
the residual 91 utility rows are a separate pattern. Treat as bonus
work, not punch-list.

### Path C — Auth / multi-tenant scoping conversation

Not a code session. Walk through the selling-motion decision
(design-partner pilot vs self-serve SaaS) so the auth-scope
decision can move forward. Per s31 handoff, this has been sitting
open across multiple sessions.

### Path D — Stop / declare ship-ready done modulo the push

If the user is satisfied with state-as-of-s32, the engine-side of
ship-ready is effectively complete. The remaining items are:
- Push of `86f710d` (their call, one command)
- BR/8 utility cluster (bonus, not blocker)
- Auth (selling-motion gated)

A reasonable framing: "Track 2 engine + renderer are stable; the
remaining work is sales-motion + ops, not engine."

### Items the user might mention but should be **declined** unless explicitly unblocked:

- **Keyword loop CP1-CP11** — out of scope per s32 (`SYSTEM_PROMPT_TRACK2_v0_1.md`
  trust order; benefits Track 1 only, not Track 2). Re-trigger only
  if user explicitly shifts focus back to Track 1 / claude.ai web.
- **Affin OCR** — out of scope per s31
  (`project_affin_ocr_deferred.md`).
- **V3-B Auto-RP SDK** — out of scope per s31
  (`feedback_no_sdk_until_bank_deploy.md`).

Whatever path: confirm `git status` + branch + test count BEFORE
any code work. Track 2 work happens only on `track-2-development`;
renderer work happens only on renderer `main` (no live feature
branch as of s32 close).
