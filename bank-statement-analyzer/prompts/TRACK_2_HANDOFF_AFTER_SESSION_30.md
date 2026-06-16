# Track 2 handoff — picking up after session 30

State at end-of-session-30 (2026-05-20). Two engine commits shipped
locally, plus a Mytutor source-file-ceiling verification and an Affin
OCR deferral with a clear gate before any further work.

**Read first:**
1. `~/.claude/projects/.../memory/feedback_source_file_ceiling.md` —
   the rule that drives all parser-quality-report verification. Source
   ceilings are not bugs to fix. Verify against raw PDF text first.
2. `~/.claude/projects/.../memory/project_ship_ready_strategy.md` —
   updated 2026-05-20 with both s30 (cheap classifier wins SHIPPED)
   and s31 (BR DATAPOS SHIPPED, Affin deferred) footers. Estimate:
   ~3-5 sessions remaining to ship-ready.
3. `~/.claude/projects/.../memory/project_affin_ocr_deferred.md` —
   **NEW.** Affin OCR work is gated on either local tesseract install
   OR Railway-prod verification. Do not start Affin parser edits
   without that gate satisfied.
4. `~/.claude/projects/.../memory/project_bimb_followups.md` —
   updated with Mytutor 99.6% UNCLASSIFIED verified as ceiling (do
   NOT design a rule pack).
5. `prompts/TRACK_2_HANDOFF_AFTER_SESSION_29.md` — predecessor.

## What landed in s30

Two Track-2-only engine commits, both **local — not pushed**. Standing
rule: no push or merge to either repo's `main` without explicit user
approval.

| # | Commit | Effect |
|---|---|---|
| 1 | `cce8e61` | **Port BUCKET_TO_CATEGORY shortcut from Track 1.** Added all 14 bucket entries + `_CATEGORY_SIDES` side-gating dict to `kredit_lab_classify_track2.py`. New dispatcher rung between C03/C04 RP and C06-C09 statutory. Mazaa Track 2: 13.1% → **91.8%** (matches Track 1 baseline). +16 tests in `tests/test_track2_bucket_dispatch.py`. |
| 2 | `7fde7c2` | **Concat-form corporate-suffix + synthetic-bucket lookup.** Two paired changes. (a) `has_corporate_suffix` gains a concat-form fallback (`_CORPORATE_SUFFIX_CONCAT_RE`) for Felcra-style glued entities (FELCRABERHAD / FELCRABINASDNBHD / KETUAEKSEKUTIFFELCRABHD-AK) — short Malaysian suffixes only, `[A-Z]{4,}` prefix guard. (b) `build_counterparty_lookup_track2` gains `include_synthetic=True` so synthetic bucket labels reach the new bucket-direct rung. Felcra Track 2: 51.0% → **86.8%** (+35.8pp). +18 tests across `test_track2_corporate_suffix.py` and `test_track2_counterparty_lookup.py`. |

**Test suite:** 1006 → **1040** (+34, all green; 6 regression skipped
by default; `RUN_REGRESSION=1` 6/6 green in ~72s).

**Mytutor verification (no code change):** Track 2 = 8046 tx, 99.6%
unclassified — **verified at ceiling** per source-file-ceiling rule.
86% are DuitNow RTP from natural-person payers (locked C26 excludes
by design); 13% are bulk-DuitNow / IBFTS-fees rows where counterparty
identity is absent from the PDF text layer. Reproduction:
`scripts/inspect_mytutor_track2_unclassified.py` +
`scripts/dump_mytutor_raw_pdf_text.py`. **Do not design a Mytutor
rule pack.**

**Affin OCR (no code change):** All 6 reference PDFs are image-only
(0 chars text layer). Local env lacks tesseract; OCR path returns
empty → 0 rows. Railway prod has tesseract via `packages.txt` but
verification of the OCR-path output is not possible from local env.
User opted to defer. See `project_affin_ocr_deferred.md`.

**Memory updates this session:**
- **NEW** `project_affin_ocr_deferred.md` — the deferral + gate
- `project_bimb_followups.md` — Mytutor verified-ceiling diagnosis
- `project_ship_ready_strategy.md` — s30 + s31 footers
- `MEMORY.md` — index entries refreshed (BIMB followups + Affin entry)

## Where we are on the ship-ready line

**Memo estimate (Apr 28):** 6-8 focused sessions to "fully sellable."
**As of 2026-05-20 (end of s30):** ~3-5 sessions remaining.

Items closed:
- ~~#2 Cheap classifier wins~~ (s30, commit `cce8e61` + `7fde7c2`)
- ~~#4 Regression suite~~ (s29, commit `1cdfe82`)
- ~~#5 Mytutor per-business-type rule~~ (s30, verified ceiling — no
  code change appropriate)

Items remaining (no specific priority enforced):
- **Bank Rakyat residuals** — 76 unclassified rows on Felcra after
  s30 fix. Most are natural-person DuitNows (locked C26 ceiling, do
  not chase). Lower-volume corpora (Cash Line statements in BR/1)
  not yet spot-checked.
- **Affin OCR** — gated on tesseract local install OR Railway prod
  verification. Don't start without the gate.
- **Renderer schema sync v6.3.3 → v6.3.5** — separate repo
  (`bank-statement-analysis-HTML-fresh/`). No parser/Track 1 risk.
  Pure plumbing per `feedback_renderer_vs_classifier.md`.
  1-2 sessions.
- **Keyword loop CP1-CP11** — touches
  `CLASSIFICATION_RULES_v3_5.json` only. Cross-bank-verify every
  keyword against actual PDF text per s29 rule.
- **#1 V3-B Auto-RP Step 2 SDK** — STILL DEFERRED per
  `feedback_no_sdk_until_bank_deploy.md`. Trigger = claude.ai web
  workflow stable. User 2026-05-18: "not stable, no need SDK."
- **#6 Auth/multi-tenant** — selling-motion decision gate.

## Out-of-scope (unchanged)

- Don't edit Track 1 files (`kredit_lab_classify.py`, `app.py`,
  `SYSTEM_PROMPT_v3_5_6.md`) without explicit user approval.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser or renderer) without explicit user
  approval.
- Don't merge `renderer-v6.3.5-support` to renderer `main` until
  user signs off.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → `track-2-development` merge unless
  explicitly scoped as a sync session.
- Don't fix classification/analysis issues in the renderer.
- Before acting on any quality-report / audit / "missed keywords"
  finding, verify against raw PDF text first per
  `feedback_source_file_ceiling.md`. Source-file ceilings are not
  bugs to fix.
- **NEW s30:** Don't start Affin OCR work without satisfying the
  gate in `project_affin_ocr_deferred.md` (tesseract local install
  OR Railway-prod OCR-output sample).

## First commands the next session should run

```bash
git status --short                                              # confirm known-dirty matches state
git branch --show-current                                       # MUST be track-2-development
git log --oneline 3acd5cf..HEAD | head                          # should show 7fde7c2 + cce8e61 + this handoff
python -m unittest discover tests 2>&1 | tail -5                # confirm 1040 / 1040 (6 skipped)
RUN_REGRESSION=1 python -m unittest tests.regression.test_snapshots 2>&1 | tail -3  # optional: 6/6 green (~72s)
git -C bank-statement-analysis-HTML-fresh branch --show-current # should be renderer-v6.3.5-support
git -C bank-statement-analysis-HTML-fresh log -1 --oneline      # should show 4244275
```

If any don't match → stop and investigate.

## Suggested first action for the next session

Recommended: **Renderer schema sync v6.3.3 → v6.3.5**.

**Why:**
- Separate repo (`bank-statement-analysis-HTML-fresh/`) — no
  parser/engine/Track 1 risk.
- Renderer is presentation-only per
  `feedback_renderer_vs_classifier.md` — bounded scope.
- No source-file-ceiling concerns; this is pure plumbing.
- The schema gap is the highest-likelihood next blocker if a real
  bank engagement materialises (engine emits v6.3.5; renderer reads
  v6.3.3 with degraded coverage).
- 1-2 sessions.

**How to approach:**
1. Read `project_html_renderer_version_gap.md`.
2. `cd bank-statement-analysis-HTML-fresh/` — verify branch
   `renderer-v6.3.5-support`.
3. Compare engine output schema (latest `track2_analysis*.json`
   under `Track 2 Files/`) against the renderer's schema-dispatch
   code.
4. Update renderer for v6.3.5 fields; preserve v6.3.3 graceful
   degradation.
5. Test against a recent engine output.

**Alternative paths if the user picks otherwise:**

- **Bank Rakyat residuals deep-dive.** 76 rows remaining on Felcra
  after s30. Triage: how many are natural-person ceiling vs real
  extractable signal? Spot-check Cash Line corpus (BR/1) too. Don't
  ship rule packs without source-text verification.
- **Keyword loop CP1-CP11.** Cross-bank-validate every keyword
  against actual PDF text per s29 rule. Touches
  `CLASSIFICATION_RULES_v3_5.json` only.
- **Affin OCR** — only after the gate in
  `project_affin_ocr_deferred.md` is satisfied (tesseract install or
  prod sample).
- **Audit Mazaa residual 41 unclassified** — low-priority follow-up
  from s30. Per `project_pbb_mazaa_followups.md`, mostly deferred
  shapes (DUITNOW TRSF DR no counterparty, GIRO PYMT singletons,
  HSE CHEQ RTN edge). Low ROI.

Whatever path: confirm `git status` + branch + test count BEFORE
any code work. Track 2 work happens only on `track-2-development`.
