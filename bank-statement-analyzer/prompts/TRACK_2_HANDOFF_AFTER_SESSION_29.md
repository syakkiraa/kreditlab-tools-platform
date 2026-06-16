# Track 2 handoff — picking up after session 29

State at end-of-session-29 (2026-05-18). Two ships this session, plus
one important strategic clarification that future sessions MUST honor.

**Read first:**
1. `~/.claude/projects/.../memory/feedback_source_file_ceiling.md` —
   **NEW this session.** Parser-quality / missed-keyword reports are
   claims to verify against source PDFs, not work lists. Chasing
   flagged misses with rule loosening breaks more than it fixes.
2. `~/.claude/projects/.../memory/feedback_no_sdk_until_bank_deploy.md`
   — updated with the explicit stability gate (user 2026-05-18: "not
   stable, no need SDK"). Defers V3-B Auto-RP Step 2.
3. `~/.claude/projects/.../memory/project_ship_ready_strategy.md` —
   has a new footer pointing to the two clarifications above.
4. `prompts/TRACK_2_HANDOFF_AFTER_SESSION_28.md` — predecessor; the
   Pattern B L5 ship.

## What landed in s29

Two engine/test commits. **All local — not pushed.** Standing rule:
no push or merge to either repo's `main` without explicit user
approval.

| # | Commit | Effect |
|---|---|---|
| 1 | `0dd21a0` | **Track 2 engine: Pattern B L5 trailing-uppercase fallback.** (Shipped earlier in this session — covered in detail in the s28 handoff.) Huahub HLB ledger 177→159 (-18); cross-bank audit clean. |
| 2 | `1cdfe82` | **Track 1 verify-harness regression suite (6 golden snapshots).** Wraps `scripts/verify_*_v3a.py` as 6 corpus snapshots under `tests/regression/`. Skip-by-default (`RUN_REGRESSION=1` to opt in). Catches drift when shared-infrastructure edits (parsers, core_utils, app.py utilities, rulebook) silently break Track 1 outputs. |

**Test suite:** 1000 → **1006** (6 regression skipped by default;
6/6 green when opted in, ~72s wall).

**Memory updates this session:**
- **NEW** `feedback_source_file_ceiling.md` — the realism rule
- `feedback_no_sdk_until_bank_deploy.md` — sharpened with stability gate
- `project_ship_ready_strategy.md` — footer pointing to both
  clarifications; ships-ready estimate updated (5-7 sessions remaining)
- `project_huahub_trial_bugs.md` — L5 fix logged (already done earlier
  in session)
- `MEMORY.md` — index entries refreshed

## The source-file-ceiling principle (critical for next session)

User flagged that parser-quality reports often misleadingly frame
*"missed keyword"* findings as code defects when they're actually
**source-file ceilings** — the bank's PDF either doesn't emit the
information, or emits it in a form text-extraction can't usably read.

**The rule (full text in `feedback_source_file_ceiling.md`):**
Before acting on any quality-report / audit / missed-keywords finding,
dump the raw PDF text and parser output and confirm the data is
actually there to extract. If it isn't, document the ceiling for that
corpus and DO NOT ship a fix. The realistic deliverable is *"deterministic
engine at the per-corpus realistic ceiling + clear escalation path to
AI for residual"* — not uniform 90%+ rates.

**Practical impact on the remaining punch list:**

| Item | Risk class |
|---|---|
| Cheap classifier wins (6-char floor, PBB prefixes, Felcra `_company_root`) | LOW — rule-level, regression-suite protected |
| Mytutor rule pack | **HIGH** — verify Mytutor PDFs actually have extractable narrative BEFORE designing the pack. If they don't, document ceiling, skip. |
| Keyword loop CP1-CP11, CIMB C05, PBB C24 | MEDIUM — cross-bank-validate every addition; never bank-specific |
| Affin OCR / Bank Rakyat DATAPOS / BIMB / RHB Waja parser edges | MIXED — verify each is a real bug, not a format limit |
| Renderer schema sync v6.3.3 → v6.3.5 | LOW — pure plumbing, unaffected |

## Where we are on the ship-ready line

**Memo estimate (Apr 28):** 6-8 focused sessions to "fully sellable."
**Reality:** ~10 sessions since the memo, but most were Huahub trial
unblocking work (6 bugs across s26-s28). One ship-ready punch-list
item closed today (#4 regression suite).

**Honest remaining (per code's reach):** ~5-7 sessions.

**Three lines you could be aiming at:**

| Definition | Distance |
|---|---|
| A. Demo-able to a bank | Already there (Huahub trial closed) |
| B. All code-reachable items shipped (calibrated engine + renderer synced + per-corpus ceiling documented) | **5-7 sessions** |
| C. Uniform 90%+ rates across all corpora | Not achievable; rate variance is partly source-file ceiling. **Closing the AI-shaped gap waits on claude.ai web stabilizing.** |

## Out-of-scope (unchanged from s28)

- Don't edit Track 1 files (`kredit_lab_classify.py`, `app.py`, `SYSTEM_PROMPT_v3_5_6.md`).
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser or renderer) without explicit user approval.
- Don't merge `renderer-v6.3.5-support` to renderer `main` until user signs off.
- Don't initiate parser or `core_utils` edits without explicit user approval.
- Don't attempt the main → track-2-development merge unless explicitly scoped as a sync session.
- Don't fix classification/analysis issues in the renderer.
- **NEW s29:** Before acting on any quality-report / audit / "missed
  keywords" finding, verify against raw PDF text first. Source-file
  ceilings are not bugs to fix.

## First commands the next session should run

```bash
git status --short                                              # confirm known-dirty matches s28 state + 2 new commits
git branch --show-current                                       # MUST be track-2-development
git log --oneline 06e9a02..HEAD | head                          # should show 1cdfe82 + this handoff
python -m unittest discover tests 2>&1 | tail -5                # confirm 1006 / 1006 (6 skipped)
RUN_REGRESSION=1 python -m unittest tests.regression.test_snapshots 2>&1 | tail -3  # optional: confirm baselines hold (~72s)
git -C bank-statement-analysis-HTML-fresh branch --show-current # should be renderer-v6.3.5-support
git -C bank-statement-analysis-HTML-fresh log -1 --oneline      # should show 4244275
```

If any don't match → stop and investigate.

## Suggested first action for the next session

Recommended: **#1 Cheap classifier wins** (6-char floor, PBB DUITNOW
prefixes, Felcra `_company_root` concatenation).

**Why:**
- Lowest-risk under the source-file-ceiling rule — these are
  rule-level improvements that don't depend on adding bank-specific
  keywords.
- Broadest cross-corpus impact short of V3-B.
- The regression suite now catches any unintended drift on the 6
  reference corpora.
- 1 session.

**How to approach:**
1. Read `project_ship_ready_strategy.md` priority order #2 detail.
2. Find each lever in `kredit_lab_classify_track2.py` (NOT Track 1).
3. Implement + unit-test in `tests/test_*.py`.
4. Run default test suite — expect green.
5. Run `RUN_REGRESSION=1` regression suite — expect green (or
   well-understood snapshot drift, in which case regenerate goldens
   in the SAME commit as the rule change with `python
   scripts/regenerate_regression_snapshots.py`).
6. Commit on `track-2-development`. Do not push.

**Alternative paths if the user picks otherwise:**
- Renderer schema sync v6.3.3 → v6.3.5 — separate repo, 1-2 sessions.
- Keyword loop CP1-CP11 — cross-bank verify each keyword against
  actual PDF text first (per s29 rule).
- Mytutor source-text investigation — **before** any Mytutor rule pack
  design; dump 50 unclassified rows + raw PDF text and decide whether
  there's anything extractable. If no → document Mytutor ceiling in
  the BIMB project memory and skip the rule pack item entirely.

Whatever path: confirm `git status` + branch + test count BEFORE any
code work. Track 2 work happens only on `track-2-development`.
