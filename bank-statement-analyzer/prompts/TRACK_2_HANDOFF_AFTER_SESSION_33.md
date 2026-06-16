# Track 2 handoff — picking up after session 33

State at end-of-session-33 (2026-05-22). Engine-side of ship-ready is
**fully closed** — s33 shipped the optional BR/8 utility cluster fix
on top of the s32 engine work, all three commits are on
`origin/track-2-development`, tests at 1076 / 1076 green, Track 1
regression 6/6 green.

The session shifted into deploy planning mid-stream. User has an
existing Railway production service tracking `main`, and we surfaced
a real **commit-level divergence** between `main` and
`track-2-development` that has to be reconciled before any
track-2-development deploy. Session paused with that sync queued but
**not executed** — user wanted a handover before running the merge.

**Read first:**
1. `~/.claude/projects/.../memory/project_ship_ready_strategy.md` —
   **UPDATED s33 footer.** BR/8 utility cluster CLOSED; push of
   `8b59baa` + `86f710d` CLOSED; new in-scope punch list is sync +
   staging service + smoke test + prod promotion. Existing Railway
   prod state documented at the bottom.
2. `~/.claude/projects/.../memory/project_track_2_branch_drift.md` —
   **UPDATED s33 footer.** Working-tree drift pattern has compounded
   into commit-level drift between `main` and `track-2-development`.
   10 commits diverge; the deploy-planning consequence (engine-better
   parser-worse staging if deployed as-is) is the s34 blocker.
3. `~/.claude/projects/.../memory/feedback_track_isolation_design.md`
   — standing rule. Track 1 must not be regressed by the merge; the
   `tests/regression/test_snapshots.py` 6-golden-snapshot suite is
   what proves this empirically.
4. `~/.claude/projects/.../memory/feedback_auto_merge_solo.md` —
   "Solo repo; ship verified fix branches by direct merge to main +
   sync derivative." This is the operating model. s34 sync is the
   "sync derivative" half.
5. `prompts/TRACK_2_HANDOFF_AFTER_SESSION_32.md` — predecessor.

## What landed in s33

One commit on parser repo, pushed to origin. Plus three memory
updates documenting the deploy-planning finding.

| # | Commit | Repo / branch | Effect |
|---|---|---|---|
| 1 | `8b59baa` (pushed) | parser `origin/track-2-development` | **Track 2 engine: BR JomPay utility merchant rung (C27).** Adds `_BR_JOMPAY_UTILITY_RE` in `kredit_lab_classify_track2.py` anchored on `CIBDRADVICE(JomPA` (BR-only opcode) with 5 verified biller tokens (DIGITELECOMMUNI, TENAGANASIONAL, PENGURUSANAIRS, INDAHWATERKONS, TMTECHNOLOGYSE). New DR-side dispatcher rung between C24 and the C26/C27 corporate-counterparty fallback fires C27 without requiring a counterparty — BR parser doesn't extract counterparty for these rows. +16 tests in new file `tests/test_track2_br_jompay_utility.py` (5 token positives + 5 FP guards + 6 dispatcher precedence). Cross-bank FP risk: zero (verified absent from BR/7, validation JSONs, ground-truth corpora). |

**Bank Rakyat re-measurement (closes the s32 punch-list item):**
- BR/8 (KOPERASIFELCRA, 4,373 tx): **90.1% → 92.2%** (+2.1pp);
  unclassified 434 → 343 (−91, exactly the cluster size).
  C27 22 → 113 (+91): DIGI 45 + TNB 19 + Pengurusan Air 15 +
  Indah Water 7 + TM 5.
- BR/7 (KOPERASIFELCRA different account, 577 tx): **90.3%
  unchanged** — no regression.
- BR/1 (Cash Line, CENFOTEC, 15 tx): **100% unchanged.**

**Tests:** 1060 → 1076 (+16, all green). Track 1 regression 6/6 green
in 72.6s. Push of `8b59baa` succeeded; push output `926ec5f..8b59baa`
revealed `86f710d` + `926ec5f` were already on `origin` (must have
been pushed between s32 close and s33 start) — end state still
matches the user's "push all 3" instruction.

## What the session shifted into mid-flight

User asked "how should I deploy on Railway?" after the BR/8 work
closed. Conversation moved through:

1. **Architecture picture** — confirmed the 3-service production
   shape: Parser app (`app.py`, this repo, USE_TRACK_2=1 surfaces
   Track 2 download button alongside Track 1 Full Report) +
   claude.ai manual step + Renderer app (separate repo
   `bank-statement-analysis-HTML`, different env var names
   `APP_USERNAME` / `APP_PASSWORD`). Fraud analyzer (`fraud_app.py`)
   is an optional 4th service from same parser repo.

2. **Track 1 / Track 2 coexistence** — same UI, same parser, same
   upload flow; `USE_TRACK_2=1` makes the Track 2 Analysis JSON
   download button appear next to the always-visible Full Report JSON
   button. User confirmed they want this shape.

3. **Branch strategy** — user proposed creating a NEW GitHub repo
   to deploy track-2-development from. Counter-proposed the lighter
   staging-service pattern: same repo, second Railway service
   tracking `track-2-development`, leaving the existing prod service
   (tracking `main`) untouched. User accepted.

4. **Branch divergence discovery** — verified the current Railway
   prod state from a user screenshot (service
   `bank-statement-analyzer-v63-production.up.railway.app`, top
   deploy `f211394` from "last week"). Then ran the actual
   `git log origin/track-2-development..origin/main` and surfaced
   that **main has 10 commits track-2-development doesn't** — 5
   unique to main (year-rollover guard, HLB retail counterparty,
   multi-account roll-up BUG-002, Maybank SME First Account-i OD,
   etc.) plus 5 same-intent-different-hash duplicates. Real
   deploy-planning blocker.

5. **Sync plan agreed.** User picked Option 1 (sync main →
   track-2-development first, then deploy staging). I created the
   todo list, started the merge work, **user paused and asked for a
   handover before execution.** No merge was run; no files were
   modified on the merge attempt. Working tree is identical to s33
   post-commit state.

## Where we are on the ship-ready line

**Post-s32 estimate:** 0-1 sessions remaining.
**Post-s33:** **0.5-1 session** remaining to clear the deploy-planning
blocker (sync) and stand up Railway staging. Prod promotion is one
merge + push after staging passes smoke-test.

**In-scope ship-ready punch list (now):**

| Item | Sessions | Status |
|---|---|---|
| 1. Sync `origin/main` → `track-2-development` | ~0.5 | **BLOCKER**, scoped + queued in s33, not yet executed. First action of s34. |
| 2. Create Railway staging service from synced `track-2-development` | ~0.3 | User-side browser clicks. See "How to do step 2" below. |
| 3. Smoke-test staging URL vs existing prod | ~0.5 | User-side. PDF upload + Track 2 download + side-by-side JSON compare. |
| 4. Promote to prod (`track-2-development` → `main` merge + push) | ~0.1 | Only after step 3 passes. Clean fast-forward once step 1 is done. |
| Auth / multi-tenant | TBD | gated by undecided selling-motion |

**Explicitly OUT of ship-ready scope (carried forward, unchanged):**

| Item | Re-trigger |
|---|---|
| Affin OCR | user explicit unblock + tesseract install OR Railway prod sample (see `project_affin_ocr_deferred.md`) |
| V3-B Auto-RP Step 2 SDK | user explicit unblock + claude.ai web workflow stable (see `feedback_no_sdk_until_bank_deploy.md`) |
| Keyword loop CP1–CP11 | user explicit shift back to Track 1 / claude.ai web (see s32 footer of `project_ship_ready_strategy.md`) |

**Items already closed (cumulative through s33):**
- ~~#2 Cheap classifier wins~~ (s30, commits `cce8e61` + `7fde7c2`)
- ~~#3 Bank Rakyat DATAPOS edge cases~~ (s30 `7fde7c2`)
- ~~#4 Regression suite~~ (s29, commit `1cdfe82`)
- ~~#5 Mytutor per-business-type rule~~ (s30, verified ceiling)
- ~~Renderer schema sync v6.3.3 → v6.3.5~~ (s31 `652099a`; s32 merged
  to renderer main + pushed)
- ~~BR residuals + Cash Line triage~~ (s32 `86f710d` — BR/7 closed,
  BR/8 substantially closed, BR/1 confirmed no-op)
- ~~Keyword loop CP1-CP11~~ (s32 cancelled with reason — Track 2
  doesn't consume rules JSON)
- ~~BR/8 utility cluster~~ (s33 `8b59baa` — closed at 92.2% on BR/8,
  zero regression on BR/7 + BR/1)
- ~~Push of `86f710d` + `8b59baa`~~ (s33 — both now on origin)

## Out-of-scope (unchanged from s32 + s33 additions)

Standing rules carried forward:
- Don't edit Track 1 files (`kredit_lab_classify.py`,
  `SYSTEM_PROMPT_v3_5_6.md`) without explicit user approval. `app.py`
  is shared and HAS been edited on track-2-development with prior
  approval (USE_TRACK_2 wire-through + s30 fixes); confirm before
  further edits.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser or renderer) without explicit user
  approval. s33's `8b59baa` push was authorized.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't fix classification/analysis issues in the renderer
  (`feedback_renderer_vs_classifier.md`).
- Before acting on any quality-report / audit / "missed keywords"
  finding, verify against raw PDF text first per
  `feedback_source_file_ceiling.md`.
- Don't start Affin OCR work without the gate in
  `project_affin_ocr_deferred.md` being satisfied.
- Keyword loop CP1-CP11 stays out of Track 2 scope per s32.

**NEW s33 (deploy-discipline):**
- **Don't touch the existing Railway prod service.** It tracks
  `main` and currently runs `f211394`. Any staging work happens in a
  SEPARATE Railway service in the same project, tracking
  `track-2-development`.
- **Don't deploy `track-2-development` without first syncing `main`
  into it.** Skipping the sync produces a staging environment that
  is engine-better but parser-worse than prod (missing year-rollover
  guard etc.) — defeats the purpose of staging.
- **Don't promote `track-2-development` → `main` until staging
  smoke-test passes.** Promotion is one merge + push and is
  irreversible without rollback complexity.

## First commands the next session should run

```bash
git status --short                                          # confirm clean tracked tree
git branch --show-current                                   # MUST be track-2-development
git log origin/track-2-development..track-2-development --oneline  # should be EMPTY (synced)
git log origin/main..origin/track-2-development --oneline | head   # should show 8b59baa at top + ~25 prior commits
git log origin/track-2-development..origin/main --oneline | head   # CRITICAL: should show ~10 commits (the divergence) — verify before merging
python -m unittest discover tests 2>&1 | tail -5            # confirm 1076 / 1076 (6 skipped)
```

If `git log origin/main..origin/track-2-development` is non-empty
before merge → someone pushed in between, re-read the diff before
proceeding.

## Suggested first action for the next session

**Path A (recommended, queued from s33) — execute the sync.**

```bash
# 1. Make sure we're on the right branch with a clean tree
git checkout track-2-development
git status --short  # must show no MODIFIED tracked files (untracked OK)

# 2. Bring origin up to date
git fetch origin

# 3. Run the merge
git merge origin/main
# If conflicts: resolve them per the conflict-handling guide below,
# then `git add <resolved-files>` and `git commit` (with the default
# merge commit message).

# 4. Verify nothing broke
python -m unittest discover tests 2>&1 | tail -5
# Expect 1076 / 1076 green (6 skipped). If something fails, the
# merge resolution is wrong — git reset --merge to abort and
# re-read the conflict files.

RUN_REGRESSION=1 python -m unittest tests.regression.test_snapshots 2>&1 | tail -3
# Expect 6/6 green in ~73s. This proves the parser fixes from main
# didn't regress Track 1's golden snapshot outputs.

# 5. Push
git push origin track-2-development
```

**Conflict-handling guide for the merge:**

Most of the 10 diverged commits on main are **same-intent /
different-hash** duplicates of fixes already on track-2-development
(both branches independently re-implemented "fix(app): preserve
`(MAYBANK` in counterparty normalisation", "fix(cimb): off-by-one
statement-month tag", etc.). For these:
- Git's three-way merge will likely auto-resolve cleanly because
  both sides arrive at the same file content via different paths
- If a conflict appears, the resolution is almost always "take the
  union" — both fixes are correct, the difference is just commit
  history shape

The 5 genuinely-unique commits on main are:
- `f211394` fix(parsers): proactive year-rollover guard for ambank,
  public_bank, rhb
- `9d4d37c` fix(maybank,app): year-rollover + RHB multi-month
  monthly_summary
- `0b9e431` maybank: support OD balance suffix (DR/CR) for SME
  First Account-i
- `39f7b1e` parsers: HLB retail / HLConnect counterparty extraction
- `ed23f43` app.py: monthly_summary multi-account roll-up (BUG-002)

These touch `maybank.py`, `public_bank.py`, `rhb.py`, `ambank.py`,
`hong_leong.py`, `app.py`. If any conflict against track-2-development's
own edits in those files, **read both sides carefully**. The
track-2-development version of `app.py` adds the USE_TRACK_2
wire-through (s24 commit `7b5aef5`); that block is NOT on main and
must survive the merge.

## How to do step 2 (Railway staging service)

After the sync push completes, the user does these in their browser
(I can't drive the Railway UI):

1. railway.app → open the existing project (the one containing
   `bank-statement-analyzer-v6.3-` service).
2. **+ New** (top right of project view) → **GitHub Repo** → select
   `luqman196/bank-statement-analyzer-v6.3-` (same repo as prod).
3. The new service deploys from `main` by default. **Stop or wait
   for that to finish**, then go to the new service's **Settings**
   tab → **Source** → change **Branch** from `main` to
   `track-2-development`. Railway re-deploys from the correct branch.
4. **Variables** tab on the new service:
   - `BASIC_AUTH_USER` = **DIFFERENT** username from prod (so analyst
     traffic stays clearly separated)
   - `BASIC_AUTH_PASS` = **DIFFERENT** strong password from prod
   - `USE_TRACK_2` = `1`
5. **Settings → Networking → Generate Domain.** Give the subdomain a
   recognizable name like `kreditlab-staging` so it's obvious which
   is which.
6. Wait 5-10 min for the first build (OCR deps are heavy).
7. Open the staging URL, expect Basic Auth prompt, log in with the
   staging credentials, expect to see 4 download buttons after PDF
   upload (CSV / XLSX / Full Report JSON / Track 2 Analysis JSON).
   If only 3 buttons → `USE_TRACK_2` env var didn't take effect.

## How to do step 3 (smoke test)

User uploads the same PDF to both prod and staging URLs.
- Track 1 Full Report JSON should be **byte-identical or
  improved** on staging (parser fixes from sync may produce slightly
  better rows; classification rules unchanged).
- Track 2 Analysis JSON (staging only) should look reasonable.
  Compare against a local `python` run of the same PDF through the
  Track 2 engine if there's any doubt.
- Check that none of the s30-s33 engine improvements caused
  surprises on familiar corpora (BR Felcra, Mytutor, Mazaa).

## How to do step 4 (promote to prod)

Only after step 3 passes. Two commands:

```bash
git checkout main
git merge track-2-development      # clean fast-forward post-sync
git push origin main
```

Existing prod Railway service auto-redeploys from main; ~5-10 min
build; analysts get the engine improvements + the parser fixes (the
latter were already there) + the Track 2 download button (if
`USE_TRACK_2=1` is set on prod — user must decide whether to
enable it on prod or keep it staging-only).

### Items the user might mention but should be **declined** unless explicitly unblocked:

- **Keyword loop CP1-CP11** — out of scope per s32. Re-trigger only
  if user explicitly shifts focus back to Track 1 / claude.ai web.
- **Affin OCR** — out of scope per s31
  (`project_affin_ocr_deferred.md`).
- **V3-B Auto-RP SDK** — out of scope per s31
  (`feedback_no_sdk_until_bank_deploy.md`).
- **BR/8 further residual cleanup** — after s33 the residual 343
  unclassified rows are scattered across PTPTN (5), Selangor
  treasury (4), LHDN (3), salary deduction refunds (3), etc. Each
  cluster is small and would need its own raw-PDF verification +
  bounded regex per `feedback_source_file_ceiling.md`. Treat as
  bonus only after deploy work is fully closed.

Whatever path: confirm `git status` + branch + test count BEFORE any
code work. Track 2 work happens only on `track-2-development`;
prod-promotion work briefly switches to `main` then returns.
