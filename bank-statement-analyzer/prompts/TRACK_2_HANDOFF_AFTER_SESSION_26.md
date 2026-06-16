# Track 2 handoff — picking up after session 26

State at end-of-session-26 (2026-05-17). Use this when starting a fresh
chat to continue Track 2 work. Session 26 cleared the three engine bugs
the Huahub trial exposed (modulo Pattern B of Fix #3) and retired a
stale documentation paragraph.

**Read first:**
1. `~/.claude/projects/.../memory/feedback_renderer_vs_classifier.md` — the masking principle
2. `~/.claude/projects/.../memory/project_huahub_trial_bugs.md` — bug log, now showing all three FIXED entries

## What landed in s26 (chronological)

Five commits across two repos. **All local — none pushed.** Per the
standing handoff rule, no push or merge to either repo's `main` without
explicit user approval.

| # | Commit | Repo / Branch | Effect |
|---|---|---|---|
| 1 | `4244275` | renderer / `renderer-v6.3.5-support` | Reverted 3 masking blocks from `acd6112`; Track 1 byte-identical to patched; v6.3.5 "12 of 6" engine bug now visible (per `feedback_renderer_vs_classifier.md`) |
| 2 | `e86a1ab` | parser / `track-2-development` | Convention-aware OD reconciliation. Detects positive-magnitude (legacy Alliance) vs signed-negative (every modern parser) at three engine sites: `_compute_opening_from_row`, `_build_monthly_for_account` reconciliation, Flag 14 `abs()` magnitude. 4 new tests. Real-data check: Huahub MBB Oct-Nov reconciles exact under fix |
| 3 | `7ee8560` | parser / `track-2-development` | Relax `SALARY_KEYWORD_RE` boundary across whole regex. Replaced `\b...\b` with `(?<![A-Za-z])X(?![A-Za-z])` so underscore-adjacent keywords match — root cause of HLB `Sep 2025_Net Pay <NAME>` being missed. Cross-bank validated against 181K descriptions: 41 real Huahub HLB salary rows newly classify; 0 regressions. 6 new tests |
| 4 | `c45b622` | parser / `track-2-development` | Counterparty Fix #3 **Pattern A**: special-bucket digit-noise strip + dedup pass. New `clean_counterparty_name` + `dedup_counterparty_entries` helpers wired into `build_track2_result` Stage 0a. Huahub 232 → 218 (collapsed 5 INTEREST + 3 UNIDENTIFIED CHEQUE + 3 BANK FEES + 2 MARKETING + 2 HUAHUB MARKETING OWN-PARTY). Cross-bank: 26K entries / 50 ledgers; zero accidental merges. 24 new tests |
| 5 | `c0cd523` | parser / `track-2-development` | Doc edit: retire stale Alliance positive-magnitude OD paragraph in CLAUDE.md. This was the misleading source that seeded the engine OD bug. Updated paragraph documents modern signed-negative default + Track 2 auto-detection + Flag 14 `abs()` + Track 1 still-on-legacy callout. **Side note**: CLAUDE.md was previously untracked (showed as `?? CLAUDE.md` at session start); commit 5 adds the whole file (+93 lines) — by intent, not accident |

**Test suite:** 970/970 pass (start of session: 933; +37 new green tests).

**Memory updates this session:**
- `project_huahub_trial_bugs.md` — now shows all three trial bugs as FIXED s26 with commit refs; Pattern B of #3 deferred
- The `feedback_renderer_vs_classifier.md` principle was applied to renderer commit 1 and engine commits 2-4 (engine fixes upstream, not renderer)

## What still needs to ship

### Fix #3 Pattern B — rail-label prefix strip (DEFERRED to s27)

The Huahub ledger still carries ~28 entries with long compound names
where the real counterparty is buried in the middle of rail-label
narrative, e.g.:

```
CR ADV-INTERBANK GIRO AT KLM 488 60 44 974 83 FIN2312259505563 7 OUG PAY OCT 25 INV _ 8 PMG PHARMACY (OUG) 6 1
```

Should become `PMG PHARMACY (OUG)`. Pattern A didn't touch these
because they don't start with a known special-bucket word.

**Why deferred:** Pattern B is a substantive design problem — needs an
anchoring strategy (corporate-suffix detection, trailing-name
heuristics, rail-label prefix table). Pattern A was risk-free + delivered
clear analyst-readability win, so it shipped independently.

**Suggested design starting point:**

1. Build a rail-label PREFIX table (`CR ADV-INTERBANK GIRO`, `CIB Instant Transfer at DIO`, `Instant Transfer at KLM`, `JomPAY Bill Payment at DIO`, `FPX B2B1`, `Fund Transfer at DIO`, `Cr Adv-Interbank GIRO at KLM`, `Inclearing-Cheque`, …). Extend the existing `_RP_EXCLUDE_PREFIXES` table or sit beside it. Audit the 28 Huahub noisy entries verbatim before locking the list.
2. Strip the prefix + the digit-run that follows it.
3. Strip the trailing recipient-bank info (`HONG LEONG BANK BERHAD(97141-X)`, `MAYBANK BERHAD`, etc.) — extract this into a separate suffix table.
4. What remains is the candidate counterparty. Apply existing `_COMPANY_SUFFIXES_RE` (already in `kredit_lab_classify_track2.py` near L1704) to anchor on SDN BHD / BERHAD / HOLDINGS / etc. when present.
5. When no corporate suffix: take the trailing N-word span before any final digit-run.
6. Extensive cross-bank validation — far higher false-positive risk than Pattern A.

Scope per s25 handoff: ~2 sessions for the full Fix #3. Pattern A took
roughly half a session (with all the design + dedup infrastructure +
tests + cross-bank validation); Pattern B is at least one full session.

### User action — re-run Huahub through the engine

The four existing engine JSONs in `Track 2 Files/Huahub Tarack 2/`
(`track2_huahub cimb.json`, `track2_huahub MBB.json`, `track2_Huahub HLB.json`,
`huahub_consolidated_analysis.json`) predate **all three engine fixes**
and still carry:
- Pre-fix #1 phantom OD reconciliation deltas
- Pre-fix #2 `salary_months_active: 0` on HLB
- Pre-fix Pattern A duplicate counterparty rows

To validate the s26 work end-to-end:
1. Re-run the parser app (Streamlit + `USE_TRACK_2=1`) on the Huahub PDFs.
2. Download the three new engine JSONs.
3. Take them through the claude.ai web prompt to produce a new consolidated analysis.
4. Render that through the renderer (still on `renderer-v6.3.5-support` branch / `4244275`).

Expected outcomes:
- DQ banner: NO "12 of 6 Months Affected" — reconciliation now passes for all OD months
- Statutory: `salary_months_active` ≥ 6 on HLB; total_salary_paid ≈ RM 20K/month
- Counterparty ledger: 218 rows instead of 232 (Pattern A reduction); names like `INTEREST`, `BANK FEES`, `UNIDENTIFIED (CHEQUE)` now bare and singular

If any of those don't hold, the engine fix has a gap worth surfacing
back to the next session.

### Renderer branch decision

`renderer-v6.3.5-support` is still local-only on its own repo. The
revert commit at `4244275` is the current HEAD. Per the standing rule,
no push or merge to renderer `main` (`12a1cf4`) without explicit
approval. Open question: ship the v6.3.5 schema support (commits
`acd6112` reverted + `4244275`) once the engine re-run validates? Or
hold until Pattern B also lands?

## Out-of-scope (unchanged + s26 additions)

Same rules as the s25 handoff, plus one s26 addition:

- Don't edit Track 1 files (`kredit_lab_classify.py`, `app.py`, `SYSTEM_PROMPT_v3_5_6.md`).
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser or renderer) without explicit user approval. ~29+ Track 2 commits + 16 handoffs sitting local since 2026-05-11.
- Don't merge `renderer-v6.3.5-support` to renderer `main` until user signs off (revert step from s25 is done; user already approved the revert commit `4244275`).
- Don't initiate parser or `core_utils` edits without explicit user approval.
- Don't attempt the main → track-2-development merge unless explicitly scoped as a sync session.
- Don't fix classification/analysis issues in the renderer (`feedback_renderer_vs_classifier.md`).
- **NEW s26:** When tempted to relax a regex word-boundary, **always** cross-bank validate first by scanning all corpora JSONs for new vs lost matches. The Net Pay fix only landed because the scan showed zero false positives. Pattern A shipped because the dedup audit showed only 6 merge groups all in the bucket allow-list. Treat /tmp/salary_boundary_diff.py and /tmp/counterparty_dedup_audit.py as templates for future cross-bank audits.

## Architecture rules (re-read before any code)

Unchanged from s25:

- Track 2 implements `CLASSIFICATION_RULES_v3_5.json` regex **verbatim** — but the s26 salary fix loosened the BOUNDARY only, not the keyword list. When relaxing a regex, audit the existing JSON corpora to confirm no new false positives.
- Track 1 is frozen. The Pattern A counterparty fix had to land as **post-processing in Track 2** because `_extract_counterparty` and `build_counterparty_ledger` live in `app.py` (Track 1).
- Schema validation is the hard gate at the engine layer. Renderer's gate is softer (warn + degrade).
- The HTML renderer lives in a separate repo (`bank-statement-analysis-HTML-fresh/`). Treat it like a different project.
- When tempted to make a renderer-side change, ask: am I fixing the display or fixing what the data should have said? The second is masking — fix it upstream.

## First commands the next session should run

```bash
git status --short                                            # confirm known-dirty
git branch --show-current                                     # MUST be track-2-development
git log --oneline 7c4bf76..HEAD | head                        # should show 4 s26 commits + this handoff
python -m unittest discover tests 2>&1 | tail -5              # confirm 970 / 970
git -C bank-statement-analysis-HTML-fresh branch --show-current  # should be renderer-v6.3.5-support
git -C bank-statement-analysis-HTML-fresh log -1 --oneline    # should show 4244275 (post-revert)
```

If any of those don't match → stop and investigate before starting any
fixes.

## Suggested first action for the next session

Two reasonable paths:

1. **Engine validation path:** Ask the user to re-run the Huahub
   pipeline (parser → engine JSON → claude.ai → render) and verify the
   three fixes work end-to-end before tackling Pattern B. This catches
   any gap in s26 work before adding more scope.

2. **Pattern B design path:** Start designing Pattern B (rail-label
   prefix strip) immediately — survey the 28 noisy Huahub entries
   verbatim, build the prefix + suffix tables, lock the anchoring
   strategy, then implement in a single careful pass with extensive
   cross-bank validation.

Path 1 is safer; path 2 makes faster forward progress.

Whatever path: confirm `git status` + branch + test count BEFORE any
code work. Track 2 work happens only on `track-2-development`.
