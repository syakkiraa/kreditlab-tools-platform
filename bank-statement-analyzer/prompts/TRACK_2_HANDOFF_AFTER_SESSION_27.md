# Track 2 handoff — picking up after session 27

State at end-of-session-27 (2026-05-18). Session 27 was a busy session:
validated the s26 engine fixes against fresh Huahub data, found and
fixed a parser-side residual, did a cross-parser audit that turned out
to be 100% false positives, and shipped Pattern B (L1+L2+L3) for
counterparty cleanup.

**Read first:**
1. `~/.claude/projects/.../memory/feedback_audit_claude_misdiagnosis.md` — now includes Pattern 3 (sub-agent loose-regex false positives, learned this session)
2. `~/.claude/projects/.../memory/project_huahub_trial_bugs.md` — now lists 4 fixed bugs + Pattern B (L1+L2+L3) partial; only L5 trailing-N-words still deferred
3. `prompts/TRACK_2_HANDOFF_AFTER_SESSION_26.md` — predecessor; the s26 engine fixes that this session validated

## What landed in s27 (chronological)

Three commits. **All local — not pushed.** Per the standing rule, no
push or merge to either repo's `main` without explicit user approval.

| # | Commit | Repo / Branch | Effect |
|---|---|---|---|
| 1 | `b7b7cf6` | parser / `track-2-development` | **CIMB parser: text-fallback for OPENING BALANCE short-row miss.** Mirrors existing `_CLOSING_RE` / `extract_closing_balance_from_text` pattern. `pdfplumber` renders the OPENING BALANCE table line as a 2-cell row that `cimb.py:512`'s `len(row) < 6` guard dropped before reaching the line-524 opening-balance handler. New `_OPENING_RE` + `extract_opening_balance_from_text` + one-line fallback at end of `parse_transactions_cimb`. 9 new tests. |
| 2 | `f49c8b9` | parser / `track-2-development` | s27 handoff (intermediate — this file replaces it). |
| 3 | `70d8cc7` | parser / `track-2-development` | **Track 2 engine: Pattern B counterparty cleanup (L1+L2+L3).** Extends Pattern A's `clean_counterparty_name`. L1 routes 3 bank-machine narrative families to existing buckets (`LOCAL/HOUSE CHEQUE (RPC) AT` → `UNIDENTIFIED (CHEQUE)`, `CDM DEPOSIT AT` → `UNIDENTIFIED (CASH)`, `SCREEN PRINT FOR STATEMENT CHARGE` → `BANK FEES`). L2 strips known rail-label prefixes (`CR ADV-INTERBANK GIRO AT KLM`, `FUND TRF FR CA TO CA-INTERNET`) and extracts via paren or corp-suffix anchor. L3 strips recipient-bank suffix tails inline within L2. 14 new tests. |

**Test suite:** 970 → 993 (+23 new green).

**Memory updates this session:**
- `feedback_audit_claude_misdiagnosis.md` — name/description widened to cover sub-agent audits, Pattern 3 added
- `project_huahub_trial_bugs.md` — fourth bug entry added for the CIMB OD opening-balance fix; Pattern B (L1+L2+L3) update needs adding (see note below)
- `MEMORY.md` — two index entries refreshed (audit-misdiagnosis description, Huahub trial-bugs description)

## What s27 validated (the s26 engine fix outcomes)

User re-ran the 3 Huahub per-bank Streamlit sessions with `USE_TRACK_2=1`
(CIMB / MBB / HLB) and dropped three fresh engine JSONs into
`Track 2 Files/Huahub Tarack 2/` (`track2_analysis.json`,
`track2_analysis (1).json`, `track2_analysis (2).json`). The 4th
consolidated session was NOT run — optional follow-up.

| Fix | Pre-s26 | Post-s26 (this session's measurement) | Verdict |
|-----|---------|-------------------------------------|---------|
| **#1** Convention-aware OD reconciliation | CIMB 6/12 FAIL + MBB 6/6 FAIL = 12 FAIL months | MBB 0/6, CIMB 11/12 → 1 residual FAIL = CIMB OD Oct 2025 | s26 fix works; residual was the new parser-side bug → fixed in s27 commit `b7b7cf6` (Huahub CIMB OD now 0/6 FAIL across all 6 months, delta=0.00) |
| **#2** SALARY_KEYWORD_RE underscore boundary | HLB 0 salary months | HLB 4 salary months (Oct/Dec/Feb/Mar) | Working. Handoff's "≥6" target was WRONG — payroll books on day-1 of next month (Nov rows dated 2025-12-01, Jan rows dated 2026-02-01), so booking-month grouping naturally gives 4 not 6. Regex confirmed matching every visible Net Pay row across the missed months. |
| **#3** Pattern A counterparty dedup | 232 entries | 228 entries | Working. Magnitude smaller than handoff's "→218" because this dataset had fewer duplicates than the original Pattern A measurement run. Noisy `"INTEREST 37 16 50 431 54"` entries collapsed cleanly into bare `"INTEREST"`. |

## What s27 added on top — Pattern B (L1+L2+L3) impact

Empirical survey (228 post-s26 counterparty entries): 49 had names ≥ 35
chars. After Pattern B:

| Layer | What it does | Cleaned entries |
|-------|--------------|------------------|
| L1 — route to existing buckets | 3 LOCAL CHEQUE (RPC) → UNIDENTIFIED (CHEQUE); 1 CDM → UNIDENTIFIED (CASH); 1 SCREEN PRINT → BANK FEES | 5 |
| L2 — paren anchor | 2 REVIVE PHARMACY (KK) variants → 1, PMG PHARMACY (OUG) | 3 (collapsed to 2 unique) |
| L2 — corp-suffix anchor | APEX CONSULTANCY SERVICES, MEDIXTRA PLT (1 entry has known "NSA MEDIXTRA PLT" limitation) | 3 |
| L3 — bank-suffix strip (inline) | Strips `HONG LEONG BANK BERHAD(97141-X)` etc. so anchor can fire | (inside L2) |

**Final corpus: 228 → 222 entries (-6).** 11 unique names cleaned.

**Cross-bank safety audit:** 18,786 unique counterparty names across 71
JSONs in `validation runs - json/` + `Track 2 Files/`. Only 17 names
total changed (5 pre-existing Pattern A INTEREST cleanups + 12
intentional Pattern B Huahub targets). **Zero accidental matches on
legitimate non-rail-label names.**

**Known limitation locked in tests:** `NSA MEDIXTRA PLT` (1 corpus occurrence)
— the leftmost-search behavior of `re.search` grabs the leading `NSA`
qualifier instead of cleaning to just `MEDIXTRA PLT`. Output is still
~80% shorter than the original 95-char narrative; documented in
`tests/test_track2_pattern_b.py:test_l2_known_limitation_*`. Future L5
work should solve this properly.

## What still needs to ship

### Pattern B L5 — trailing-N-words fallback (DEFERRED)

The risky piece of Pattern B. Without L5, ~10-15 Huahub entries that
have neither paren nor corp-suffix anchor stay as the full narrative:
- 8× `AEON CO` (in `... AEON PAYMENT 0000102284 AEON CO _ 7` shapes)
- `BESTARI HEALTH CARE` (3 words, no anchor)
- `CITY PHARMACY`, `MEDWISE PHARMACY`, `PASTEL CARE` (2 words, no anchor)
- `BEMED TEMPUA` (probably-real CP, unclear)
- `F IMAN FARMASI IMAN` (messy/duplicated, unclear true CP)

**Design starting point (per s26 handoff + s27 implementation experience):**

1. Strategy: after L2 strips known rail-label prefix, scan remainder
   right-to-left. Strip trailing `[\d\s_]+`. Take the trailing N
   UPPERCASE words (2-3) up to the first non-uppercase token.
2. Stop-word list to skip: `PAYMENT`, `INVOICE`, `TRANSFER`, `WAGES`,
   `PROMOTION`, `MARKETING`, `DEPOSIT`, etc. — generic operational
   words that aren't counterparty names.
3. Cross-bank validation: 18K-corpus audit template already used in
   s27 (Pattern B audit). Repeat for L5; expect ~30-50 names changed
   vs the current 12.
4. Risk: trailing-word strategy will catch some genuine descriptions
   like `TRANSFER FOR 2024 INVOICE → INVOICE` (wrong). Mitigated by L2
   gate (only fires after known rail-label prefix), but stop-word list
   needs careful curation.

**Effort:** ~1 session (less than the original Pattern B since the
plumbing is already in `clean_counterparty_name`).

### User action — optional: re-run with consolidated session

If you want to verify the consolidated 4-account roll-up reconciliation
works clean, do a single Streamlit session with all 24 Huahub PDFs
together and download. The 3 per-bank JSONs already verify the
per-account paths. After the s27 fixes, the consolidated JSON should
show 0/24 month-row FAILs, 4 HLB salary months, and a slightly-smaller
counterparty count via Pattern B dedup.

The Streamlit server (`USE_TRACK_2=1` + `python3 -m streamlit run app.py`)
was launched in s27 as background task `b33aysy2e` on port 8501 with
basic auth `dev` / `dev`. May or may not still be running depending on
whether the user shut it down.

### Renderer branch decision (unchanged from s26)

`bank-statement-analysis-HTML-fresh/` is on `renderer-v6.3.5-support`
at `4244275` (post-revert). No push or merge to renderer `main` without
explicit approval. Once Pattern B output is verified through a full
re-render, the renderer branch is shippable.

## What s27 learned about audit reliability

A `general-purpose` sub-agent audited 4 parsers (PBB, BIMB, Muamalat,
UOB) for the CIMB-shaped "OPENING BALANCE row dropped" bug and returned
BUG verdicts on all 4. **All 4 were false positives.** Re-audit across
full corpora (parser → engine reconciliation across 17+39+6+30 PDFs
respectively) showed **0 month-row FAILs across every bank**. The
sub-agent's regex was too loose — it conflated `Balance B/F`,
`Balance C/F`, `Balance From Last Statement`, and mid-statement
carryforwards as if they were all "the opening line", then compared
engine-derived opening against whichever amount its grep caught first.

This is now documented as Pattern 3 in `feedback_audit_claude_misdiagnosis.md`.
The principle generalises beyond claude.ai web audits to ANY audit
verdict, including ones I spawn via the Agent tool. **Before acting on
any multi-target fix list, run the parser → engine reconciliation
across the full corpus per flagged bank. If reconciliation is clean,
don't fix speculatively.**

The user's "don't take shortcuts" challenge was the right move — it
forced the re-audit that would otherwise have shipped 4 dead-code or
actively-harmful "fixes" to working parsers. PBB specifically would
have broken: my draft `extract_opening_balance_from_text` matched the
page-2 carryforward `Balance B/F 412,996.87` as if it were opening, and
would have injected a synthetic OPENING BALANCE row with that (wrong)
value, corrupting reconciliation on every PBB statement.

## Out-of-scope (unchanged from s26)

- Don't edit Track 1 files (`kredit_lab_classify.py`, `app.py`, `SYSTEM_PROMPT_v3_5_6.md`).
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser or renderer) without explicit user approval.
- Don't merge `renderer-v6.3.5-support` to renderer `main` until user signs off.
- Don't initiate parser or `core_utils` edits without explicit user approval (s27 confirmed why — the re-audit principle protects against the same overreach).
- Don't attempt the main → track-2-development merge unless explicitly scoped as a sync session.
- Don't fix classification/analysis issues in the renderer.
- **NEW s27:** Before acting on any audit's fix list, run parser → engine reconciliation across the full corpus per flagged bank. Speculative fixes for hypothetical PDFs violate "no shortcuts" exactly as much as missing real bugs does.

## First commands the next session should run

```bash
git status --short                                            # confirm known-dirty matches s26 state + 3 new commits
git branch --show-current                                     # MUST be track-2-development
git log --oneline c03bc24..HEAD | head                        # should show 3 s27 commits + this handoff
python -m unittest discover tests 2>&1 | tail -5              # confirm 993 / 993
git -C bank-statement-analysis-HTML-fresh branch --show-current  # should be renderer-v6.3.5-support
git -C bank-statement-analysis-HTML-fresh log -1 --oneline    # should show 4244275
```

If any don't match → stop and investigate.

## Suggested first action for the next session

Three reasonable paths, roughly ordered by ROI vs risk:

1. **Pattern B L5 (trailing-N-words fallback):** Closes the last
   ~10-15 Huahub noisy entries that have no inline anchor. ~1 session.
   Design notes above. Highest cross-bank false-positive risk of any
   Pattern B layer — use the 18K cross-bank corpus audit template
   (see `/tmp/` scratch from s27 if still present, else rebuild from
   the validation runs JSONs).

2. **Renderer schema sync v6.3.3 → v6.3.5** (own repo): Switch to
   `bank-statement-analysis-HTML-fresh/`, sync schema, then ship the
   v6.3.5 support to renderer `main` (after the user signs off on the
   `acd6112` revert + Pattern B output rendering correctly). 1-2
   sessions; bumps renderer past warn-and-degrade state.

3. **Ship-readiness lever per `project_ship_ready_strategy.md`:**
   memo says "engine ~6-8 sessions away" with V3-B Auto-RP Step 2 as
   the biggest rate-variance lever. Re-read the strategy memo to lock
   the next engine session's scope.

Pattern B L5 closes the Huahub trial completely. Path 2 unblocks
analyst-facing improvements. Path 3 progresses MVP. User decides.

Whatever path: confirm `git status` + branch + test count BEFORE any
code work. Track 2 work happens only on `track-2-development`.
