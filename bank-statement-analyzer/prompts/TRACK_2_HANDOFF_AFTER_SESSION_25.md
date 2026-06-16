# Track 2 handoff — picking up after session 25

State at end-of-session-25 (2026-05-17). Use this when starting a fresh
chat to continue Track 2 work. This session was meant to be the Huahub
trial wrap-up — instead it surfaced **three real Track 2 engine bugs** and
established a hard principle: the renderer must never mask classifier
bugs.

**Read first:**
1. `~/.claude/projects/.../memory/feedback_renderer_vs_classifier.md` — the principle
2. `~/.claude/projects/.../memory/project_huahub_trial_bugs.md` — the three engine bugs

The fix plan below is the concrete next-session sequencing.

## What happened in s25

The user booted the patched parser app from s24 with `USE_TRACK_2=1`,
ran the Huahub multi-bank trial through claude.ai, downloaded the
analysis JSON, and produced the first analyst-facing HTML from the
Railway-deployed renderer. **Result was unshippable.**

Diagnosed defects fell into two buckets:

- **Real engine/classifier bugs (Track 2 side):** OD reconciliation
  formula uses Alliance unsigned-magnitude convention but Huahub's CIMB
  Islamic OD + MBB Islamic OD emit Ambank-convention signed-negative
  balances; salary regex doesn't catch HLB "Net Pay" phrasing;
  counterparty extractor leaves rail-label noise in names and doesn't
  merge variants. See `project_huahub_trial_bugs.md` for full breakdown.
- **Renderer presentation bugs:** mojibake on Railway-deployed HTML
  (UTF-8 written, latin-1 read on file:// open); schema-version gap
  (renderer accepts v6.0.0–v6.3.3, JSON is v6.3.5); counterparty
  cleanup cards rendered as "0/0/0" instead of hidden when absent.

I patched both sets renderer-side. **The user pushed back:** never fix
classification bugs in the renderer. The right fix for engine bugs is in
the engine (or rulebook, or prompt) — not in the presentation layer.
The renderer should display whatever the JSON says, faithfully, even
when the JSON is wrong, so the underlying bug stays visible and gets
prioritised.

This is now hard rule: `feedback_renderer_vs_classifier.md`.

## State of the renderer branch — needs revert pass

**Branch:** `renderer-v6.3.5-support` in `bank-statement-analysis-HTML-fresh/`
(separate repo, separate `.git/`). One commit:

```
acd6112 v6.3.5 renderer support — Track 1 byte-identical, fixes Track 2 deliverable
```

The commit changed `app.py`: +121 / −27 lines. Six patches in the diff:

| # | Patch | Category | Keep / Revert |
|---|---|---|---|
| 1 | Schema-version tuples: add `'6.3.4', '6.3.5'` to `is_v620`, `is_v630`, accepted-list at L3105, expose `is_v635` | Presentation (schema dispatch) | **Keep** |
| 2 | New `normalize_claude_v635()` shim — first half: rescale `overall_success_rate * 100` if decimal | Presentation (number format) | **Keep** |
| 3 | New `normalize_claude_v635()` shim — second half: dedupe `months_with_gaps`, tag `_dq_class_v635` when no extraction gaps | **Masking** — re-derives engine signal | **REVERT** |
| 4 | DQ banner "Reconciliation Mismatch (Sign Convention)" amber copy when `_dq_class_v635 == 'RECON_MISMATCH_ONLY'` | **Masking** — softens copy on a real engine bug | **REVERT** |
| 5 | `_cov_bar` EPF/SOCSO fallback to `epf_coverage_pct` when salary base = 0 | **Masking** — engine's salary regex failed; renderer shouldn't paper over it | **REVERT** |
| 6 | Hide counterparty cleanup cards (Original/Merges/Purpose Strips) when all = 0 | Presentation (don't show empty zeros) | **Keep** |
| 7 | UTF-8 download: `html_content.encode('utf-8')` + `text/html; charset=utf-8` MIME | Presentation (encoding) | **Keep** (note: didn't fully fix mojibake on file:// open — may need BOM addition `﻿` at HTML start) |

**Regression baseline already exists.** Pre-patch HTML for 7 Track 1
schemas (v6.0.0, v6.2.2, v6.3.1×3, v6.3.3×2) is at
`/tmp/renderer-regression/baseline/v*.html`. 6 of 7 were byte-identical
under the full patch; the 7th differed only in the cleanup-card-hide
change (which we're keeping). After reverting patches #3-5, expect
byte-identical to baseline for ALL 7 Track 1 files. **Re-run the
regression** before merging anything.

**Branch state:**
- Local-only on `renderer-v6.3.5-support`
- NOT pushed to origin
- NOT merged to renderer's `main` (`main` is still at `12a1cf4`)
- The patched renderer was booted on local port 8502 during s25 (may
  have been killed; user closed the chat)

**Streamlit instance:** as of end-of-session, port 8502 was running the
patched renderer (PID 28091). If still alive, kill it before re-rendering.

## Track 2 engine fix plan — three workstreams, in order

### Fix #1: OD reconciliation sign-convention (HIGHEST LEVERAGE)

**File:** `kredit_lab_classify_track2.py` (Track 2 engine, in main repo)

**Bug:** Engine applies `opening + DR − CR = closing` (Alliance unsigned
convention) for ALL OD accounts. CIMB Islamic OD 8605964920 and MBB
Islamic OD 564342645726 emit signed-negative balances (Ambank
convention). Result: 12 of 24 month-checks fail with non-zero
`reconciliation_delta` even though closing balances are correct. Five
of six CIMB OD months reconcile EXACTLY under `opening + CR − DR =
closing` (I verified this re-derivation during s25).

**Fix shape:** Make OD reconciliation bank-convention-aware. Detect the
convention from the sign of `opening_balance` for `is_od=True` accounts
— if negative, use the Ambank formula. CLAUDE.md L65 documents both
conventions; this is the "#1 source of false positives in the audit."

**Regression test:** Must NOT regress Alliance OD (positive
unsigned-magnitude balances). Use `Bank-Statement/Alliance/*` corpora as
baseline; new test case is `Track 2 Files/Huahub Tarack 2/track2_huahub
cimb.json` + `track2_huahub MBB.json`.

**Expected outcome:** `total_balance_checks_passed` 12/24 → 24/24 on
Huahub. `data_completeness` flips to COMPLETE. Renderer DQ banner stops
firing entirely — no renderer copy fix needed.

**Scope:** ~1 session.

### Fix #2: Salary regex / "Net Pay" detection (RULEBOOK)

**File:** `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`

**Bug:** Salary keyword set doesn't match HLB's `Sep 2025_Net Pay
<NAME>` phrasing. Engine reports `salary_months_active: 0,
total_salary_paid: 0` despite obvious monthly payroll to 5 named HLB
employees. EPF/SOCSO/LHDN are still detected (own rungs), so COMPLIANT
verdict survives — but `total_salary_paid` is structurally RM 0.

**Fix shape:** Use the keyword-loop workflow in
`prompts/improve_keywords.md`. Add `Net Pay`, `NETPAY`, `NET_PAY`
variants to the salary keyword/example set. Validate cross-bank per
`feedback_crossbank.md` (must not over-fire on other banks).

**Regression:** Re-classify existing corpora to confirm no new
salary-tag false positives.

**Expected outcome:** `salary_months_active` 0 → 6 (HLB monthly payroll
detected). `total_salary_paid` populates with ~RM 20K/month estimate.
EPF coverage card in HTML displays naturally without needing renderer
fallback.

**Scope:** ~30 min interactive (keyword loop pattern is well-trodden).

### Fix #3: Counterparty extraction + dedup (ENGINE, larger)

**File:** `kredit_lab_classify_track2.py` (counterparty extractor logic)

**Two sub-fixes:**

**(3a) Strip rail-label prefix from counterparty names.** Engine
currently emits names like:
```
CR ADV-INTERBANK GIRO AT KLM 488 60 44 974 83 FIN2312259505563 7 OUG PAY OCT 25 INV _ 8 PMG PHARMACY (OUG) 6 1
```
Should be `PMG PHARMACY (OUG)`. Fix: anchor on SDN BHD / SDN. BHD. /
corporate suffix when present and take the span ending there. When
absent, strip everything before known rail labels: `CR ADV-INTERBANK
GIRO AT KLM`, `CIB Instant Transfer at DIO`, `Instant Transfer at
KLM`, `JomPAY Bill Payment at DIO`, `FPX B2B1`, `Fund Transfer at
DIO`, `Cr Adv-Interbank GIRO at KLM`, `Inclearing-Cheque`, etc. The
rail-label set is similar to what s23's RP3 false-positive filter
already enumerates (`_RP_EXCLUDE_PREFIXES`) — extend that table.

**(3b) Post-extraction dedup pass.** Huahub's 232-row ledger contains:
- `UNIDENTIFIED (CHEQUE)` × 3 (one per bank's cheque bucket)
- `INTEREST` × 5 (each monthly profit credit gets its own row because
  the row body is in the name)
- `BANK FEES` × 3
- `HUAHUB MARKETING (OWN-PARTY)` × 2
- `MARKETING` × 2

Normalize the name (strip trailing numbers, case-fold, collapse runs of
spaces) and merge rows that match. Sum credits + debits + tx counts;
concatenate transactions lists.

**Regression:** Existing single-bank corpora (Upell, MTC OD, Mazaa)
shouldn't have many duplicates; verify the dedup doesn't accidentally
merge legitimately distinct counterparties.

**Expected outcome:** Huahub counterparty ledger 232 rows → ~100 rows.
Names are clean and useful for analyst review. Renderer doesn't need
any counterparty-side logic.

**Scope:** ~2 sessions (extraction is delicate, dedup is straightforward).

## Sequencing

| # | Step | Effort | Blocked by |
|---|---|---:|---|
| 1 | Revert 3 masking patches from `renderer-v6.3.5-support` (regen HTML, byte-diff against Track 1 baselines, confirm all 7 byte-identical) | 15 min | nothing |
| 2 | Fix #1 — OD reconciliation Ambank-convention support in engine | 1 session | nothing |
| 3 | Fix #2 — salary keyword loop for `Net Pay` variants | 30 min | nothing |
| 4 | Fix #3 — counterparty extraction + dedup in engine | 2 sessions | nothing |
| 5 | Re-run Huahub: parser → 3 new engine JSONs → claude.ai → new analysis JSON → render | depends on user | Fixes 1-3 |
| 6 | Decide on merging `renderer-v6.3.5-support` to renderer's main + Railway deploy | discussion | Step 1 done |

Steps 2, 3, 4 are independent — can be done in any order or in
parallel sessions. Step 1 should happen first regardless (clears the
masking patches).

## Artifacts from the Huahub trial (DO NOT DELETE)

In `Track 2 Files/Huahub Tarack 2/`:
- `track2_huahub cimb.json` — engine JSON (2 CIMB accounts, 1 Current + 1 Islamic OD)
- `track2_Huahub HLB.json` — engine JSON (HLB Islamic Current)
- `track2_huahub MBB.json` — engine JSON (MBB Islamic OD)
- `huahub_consolidated_analysis.json` — claude.ai Deliverable 1 (v6.3.5)
- `huahub_parser_quality_report.md` — claude.ai diagnostic markdown

These are the regression / verification set for all three engine fixes.

## Tests + commits — what s25 added vs touched

**Parser repo (`track-2-development` branch):**
- No code commits in s25. Working tree state matches start-of-session
  (known-dirty untracked items from other workstreams). Test count
  unchanged at 933/933 (verified at start of session).
- This handoff document is the only new file to commit.

**Renderer repo (`renderer-v6.3.5-support` branch):**
- One commit `acd6112` (the 6-patch bundle).
- Needs partial revert (patches #3, #4, #5 — see table above).

**Memory updates (saved this session):**
- `feedback_renderer_vs_classifier.md` (NEW) — the principle
- `project_huahub_trial_bugs.md` (NEW) — the three engine bugs
- Both indexed in `MEMORY.md`

## First commands the next session should run

```bash
git status --short                                            # confirm known-dirty
git branch --show-current                                     # MUST be track-2-development
git log --oneline c9c8d30..HEAD | head                        # should show 7 commits (s22-s24 + s25 handoffs)
python -m unittest discover tests 2>&1 | tail -5              # confirm 933 / 933
git -C bank-statement-analysis-HTML-fresh branch --show-current  # should be renderer-v6.3.5-support
git -C bank-statement-analysis-HTML-fresh log -1 --oneline    # should show acd6112
```

If `renderer-v6.3.5-support` doesn't exist or `acd6112` isn't there →
stop and investigate before starting any fixes.

## Out of scope for next session — unchanged + one addition

- Don't edit Track 1 files.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser repo or renderer repo) without explicit user approval. **Twenty-five+ Track 2 commits + fifteen handoffs** sitting local since 2026-05-11.
- Don't merge `renderer-v6.3.5-support` to renderer's `main` until the revert pass (step 1) is done AND user signs off.
- Don't initiate parser or `core_utils` edits without explicit user approval.
- Don't attempt the main → track-2-development merge unless explicitly scoped as a sync session.
- **NEW (s25):** Don't fix classification/analysis issues in the renderer. Renderer is presentation only. Engine/rulebook/prompt is where classification bugs get fixed. See `feedback_renderer_vs_classifier.md`.

## Architecture rules (re-read before any code)

Unchanged from previous handoffs:

- Track 2 implements `CLASSIFICATION_RULES_v3_5.json` regex **verbatim**.
  When the parser emits a bank-specific shape that the LOCKED rule
  doesn't cover, lock it as a corpus-gap test — do NOT widen the Track
  2 regex without updating v3.5 first.
- Track 1 (`kredit_lab_classify.py`, `SYSTEM_PROMPT_v3_5_6.md`) is
  **frozen**. Track 2 must not import from it.
- Schema validation is the hard gate at the **engine** layer.
  Renderer's gate is softer (warn + degrade). Both need to be
  satisfied for end-to-end analyst delivery.
- The HTML renderer lives in a **separate repo** (`.git/` inside
  `bank-statement-analysis-HTML-fresh/`). Treat it like a different
  project — don't accidentally edit it while doing Track 2 parser
  work.
- **NEW:** When tempted to make a renderer-side change, ask: am I
  fixing the display or fixing what the data should have said? The
  second is masking. Fix it upstream.

## Suggested first action for the next session

Two paths depending on user's energy:

1. **Pure technical path:** "Start with step 1 (revert masking patches) — give me the diff before committing." Then proceed to step 2 (OD reconciliation fix). This is the cleanest sequencing.

2. **Discussion path:** "Before any code, review the three engine bugs (`project_huahub_trial_bugs.md`) and decide priority + scope." Useful if the user wants to defer fix #3 (counterparty), or wants to discuss whether v6.3.5 `overall_success_rate` decimal-vs-percent is a renderer or engine concern.

Whatever path: confirm `git status` + branch + test count BEFORE any
code work. Track 2 work happens only on `track-2-development`.
