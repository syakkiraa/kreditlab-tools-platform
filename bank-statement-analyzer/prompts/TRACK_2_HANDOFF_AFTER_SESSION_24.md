# Track 2 handoff — picking up after session 24

State at end-of-session-24 (2026-05-17). Use this when starting a fresh
chat to continue Track 2 work — specifically, the **Huahub multi-bank
trial that was in mid-flight** when this session wrapped.

## Current state

**Branch:** `track-2-development` at commit `7b5aef5`. Two Track 2 code
commits landed in this session (s23 and s24), plus one handoff commit
(`b6b7f8d` — the previous handoff this session picked up from).

**Test count:** 933 / 933 (911 from previous + 11 from s23 + 11 from s24).

**Track 2 code commits added in s23 + s24:**

| Commit | Files | Tests | Role |
|---|---|---|---|
| `263d79f` | `kredit_lab_classify_track2.py`, `tests/test_track2_rp_false_positive_filter.py` | +11 | s23 — RP3 scanner false-positive filter: extended `_RP_EXCLUDE_PREFIXES` with rail-label tokens (`TRSF`, `RMT`, `IBG`, `CHEQ`, `DEP-ECP`, `DR-ECP`) + added `OWN_PARTY_MARKER_RE.search` check inside `scan_related_party_candidates` |
| `7b5aef5` | `app.py`, `kredit_lab_classify_track2.py`, `tests/test_track2_account_meta_bridge.py` | +11 | s24 — app.py Track 2 wire-through: `USE_TRACK_2=1` env var, new `account_meta_from_determinations()` bridge in the engine, gated download button in app.py |

## What sessions 23 + 24 accomplished

### s23 — RP3 false-positive filter

Closed the loop on the only finding s22's `report_info.related_parties`
population surfaced — synthetic bucket labels (`TRSF DR`, `PRINCIPAL
GAS (OWN-PARTY)`, etc.) auto-confirming as Affiliates. Side-by-side
on Mazaa + Principal Gas verified the predicted outcomes: Mazaa drops
`TRSF DR` to empty list; Principal Gas drops the OWN-PARTY synthetic
bucket but retains the real `MERCHANT STREET` RP.

### s24 — app.py wire-through (first analyst-trial enabler)

Added `USE_TRACK_2` env var gating a new `🔬 Download Track 2 Analysis
(JSON)` button in the Streamlit parser app. Conditional engine import
keeps cold-start byte-identical when flag is off (AST audit confirmed
zero unguarded references). New `account_meta_from_determinations()`
bridge in `kredit_lab_classify_track2.py` projects the
`account_type_determinations` list `app.py` builds into the
`{account_no: {is_od, account_type, od_limit}}` shape the engine
expects, with **OD-wins semantics** across multi-PDF same-account
inputs.

### Live trial run on 3 corpora (after s24)

The wire-through was field-validated against three real corpora — all
pass:

| Trial | Bank | Account | Type | Highlights |
|---|---|---|---|---|
| **Mazaa** | Public Bank | 3814592414 | Current | `total_own_party_cr = RM 941,100.00` matches s23 prediction to the ringgit; `related_parties = []` (rail-label filter holds) |
| **Upell** | UOB | 2563024579 | OD ✓ | OD locked via Rule 3 (sustained negative balance); opening `-543,460`, closing `-580,376` |
| **MTC OD** | Ambank | 0742022008052 | OD ✓ | OD locked via Rule 2 (DR-suffix); Ambank negation convention applied correctly |

All three: schema-valid, correct account_type routing via the new
bridge, zero rail-label false positives in `report_info.related_parties`.

## Mid-flight: Huahub multi-bank trial

**Status: parser runs pending — user wraps the conversation before
starting them.** The pre-analysis template and operational plan are
already in place:

- **Template:** `prompts/RUN_INPUT_FILLED_HUAHUB.md` (NEW untracked
  file this session) — multi-bank pre-analysis input for HUAHUB
  MARKETING SDN BHD across CIMB (2 accounts: 4920 + 9504), Hong Leong
  (28900032761), Maybank (5726). 4 accounts × 6 months (Oct'25 – Mar'26)
  × 3 banks.
- **Plan (5 steps):**
  1. Three parser Streamlit runs (one per bank dropdown) → produce 3
     Track 2 JSONs (CIMB, HLB, MBB)
  2. Open new chat in **Kredit Lab — Track 2** claude.ai project,
     paste filled pre-analysis block + drag all 3 JSONs in one message,
     send
  3. Save claude.ai Deliverable 1 (analysis JSON) as
     `huahub_analysis_v635.json`
  4. Boot the HTML renderer Streamlit (`bank-statement-analysis-HTML-fresh/app.py`)
     on a different port (e.g. 8502), upload the analysis JSON,
     download HTML + Excel
  5. Review the HTML — that's the actual analyst-facing artifact and
     the trial verdict

The user will run steps 1-3 between sessions. Next session likely
picks up at step 4 (boot the renderer) OR step 5 (review the rendered
HTML).

## NEW pipeline context discovered this session

**The Track 2 pipeline has FOUR stages, not three.** Memory entry
saved: `project_track2_html_pipeline.md`.

```
PDFs
  → parser Streamlit (app.py + USE_TRACK_2=1)
  → engine JSON (track2_analysis.json, v6.3.5)
  → claude.ai web (Kredit Lab — Track 2 project, SYSTEM_PROMPT_TRACK2_v0_1.md)
  → analysis JSON (v6.3.5 schema, Deliverable 1 + Deliverable 2)
  → HTML renderer Streamlit (bank-statement-analysis-HTML-fresh/app.py)
  → HTML deliverable (the analyst's actual hand-off to credit committee)
```

The v6.3.5 schema is the **contract between claude.ai's analysis JSON
and the HTML renderer**, not just an engine-side validation gate.

## HTML renderer version gap (NEW this session)

Memory entry saved: `project_html_renderer_version_gap.md`.

Renderer (`bank-statement-analysis-HTML-fresh/app.py`, 3278 lines,
separate `.git/` inside the folder, Python 3.11.8 per `python-version`,
deps: `streamlit==1.41.0` + `openpyxl>=3.1.0`) accepts schemas
`6.0.0`–`6.3.3`. Engine + Track 2 v0.1 prompt are on **v6.3.5** — two
minor versions ahead.

- Renderer **warns + degrades gracefully** on unknown versions (line
  3105): `st.warning("Expected schema v6.0.0–v6.3.3, got v{X}. Some
  features may not work correctly.")`. Does NOT reject.
- v6.3.4 / v6.3.5-only fields silently absent from HTML.
- Renderer accepts **ONE JSON at a time** — multi-bank consolidation
  must happen at the claude.ai step.
- `normalize_claude_v633()` shim (L308) reshapes claude.ai analysis
  JSON to renderer's internal layout — confirms pipeline is "AI output
  → normalizer → renderer".

**Path forward:** proceed with v6.3.5 outputs and treat missing HTML
fields as a punch list for a future renderer-sync session (1-2
sessions of work in the HTML repo). Do NOT downgrade the engine /
prompt to v6.3.3.

## Sync state vs main

Still 19+ commits behind main. Unchanged. Defer.

## Cumulative state across sessions 1-24

**Engine feature-complete + s22 + s23 + s24 fixes.** Tier 4 prompt
v0.1 validated against:
- 2 of 6 verify corpora via formal smoke (Principal Gas, Mazaa — both
  STRONG PASS)
- 3 of 3 live trial corpora via the wire-through (Mazaa, Upell, MTC OD
  — all schema-valid, correct account_type routing)
- 1 multi-bank trial in progress (Huahub — pending)

**MVP ship verdict: still GO.** Engineering milestone hit at s24 (the
analyst trial is unblocked).

## Open items the user can tackle next

### Option 1 — Finish the Huahub trial (Recommended IF user has run steps 1-3)

If the user comes back with `track2_huahub_cimb/hlb/mbb.json` AND the
claude.ai analysis JSON in hand:

1. Boot the HTML renderer on port 8502:
   ```bash
   cd "bank-statement-analysis-HTML-fresh"
   # Reuse the parser repo's venv OR create renderer-local venv
   APP_USERNAME=admin APP_PASSWORD=admin \
   ../.venv/bin/python -m streamlit run app.py \
     --server.address=127.0.0.1 --server.port=8502 --server.headless=true \
     --browser.gatherUsageStats=false
   ```
   Note: renderer's `python-version` is 3.11.8 but the parser repo venv
   is on 3.9.6. Renderer deps (`streamlit==1.41.0`, `openpyxl>=3.1.0`)
   are 3.9-compatible — should work, but verify.
2. Open http://127.0.0.1:8502, login (env vars above), upload the
   analysis JSON.
3. Download HTML + Excel.
4. Review HTML — that's the trial verdict.

### Option 2 — Investigate Huahub trial blockers

If steps 1-3 hit a problem (parser crash, claude.ai issue, etc.), debug
that. The most likely failure modes:
- **Multi-bank context overload in claude.ai:** AI struggles with 3
  simultaneous JSON attachments. Fallback: 2-step approach (Chat 1:
  CIMB + HLB → partial analysis; Chat 2: all 3 engine JSONs + Chat
  1's output → final consolidated analysis).
- **Parser run failure on Huahub PDFs:** specific PDF format
  variations. Inspect the failing PDF's page 1 + the parser stderr.

### Option 3 — HTML renderer sync to v6.3.5 (parallel workstream)

Separate workstream in the HTML repo (`bank-statement-analysis-HTML-fresh/`).
Estimated 1-2 sessions:
1. Add `'6.3.4'`, `'6.3.5'` to the accepted-versions tuple at L3105.
2. Build rendering for any v6.3.4/v6.3.5-only fields. (Spec lives in
   the engine's schema validator + the v0.1 prompt's Deliverable 1
   schema reference.)
3. Test against existing analysis JSON outputs in `validation runs -
   json/22 april 2026 - result HTML(MTA,KYDN,MSSB)/` and the in-progress
   Huahub output.

Pre-req: needs explicit user approval before touching the HTML repo's
git history (separate repo, separate ship cadence).

### Option 4 — v0.2 prompt edits (cosmetic, ~30 min, deferred from s22)

Three small edits to `prompts/SYSTEM_PROMPT_TRACK2_v0_1.md`:
1. `total_rm` → `total_amount` typo (§8 line 285)
2. §3.1 Flag #4 vs #9 disambiguation
3. §6 "dates and amounts copied verbatim" hard rule

~30 min total. Rename to v0.2 + bump §9 version line.

### Option 5 — Remaining 4 Tier-4 corpora smokes (Felcra, Waja, KMZ, Mytutor)

Single-bank smokes following the Mazaa / Principal Gas template. Gives
v0.x a 6-of-6 evidence base. ~30 min interactive per corpus.

### Blocked items (unchanged from s22)

- C12 deterministic FD/interest detector — no detector ported.
- CIMB AI_ASSIST — Tier 4 prompt territory.
- Principal Gas multi-bank consolidation — needs the same multi-bank
  handling the Huahub trial is currently testing.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path. The s23 + s24 commits
followed this — only the named Track 2 paths were staged.

**Untracked Track 2 prompts not committed yet (likely to commit with
this handoff):**
- `prompts/RUN_INPUT_FILLED_HUAHUB.md` — the multi-bank pre-analysis
  template drafted in this session.

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline c9c8d30..HEAD                 # should show 6 commits (4 + s23 + s24, plus this handoff)
python -m unittest discover tests 2>&1 | tail -5  # confirm 933 / 933
```

Expected `git log` (top-down, newest first):
```
<this-handoff-commit> prompts: Track 2 session-25 handoff (after session 24)
7b5aef5 Track 2 session 24: app.py wire-through (USE_TRACK_2 flag + engine download)
263d79f Track 2 session 23: RP3 scanner false-positive filter (rail labels + OWN-PARTY)
b6b7f8d prompts: Track 2 session-23 handoff (after session 22)
f7b9a85 Track 2 session 22: engine fixes #1 + #2 from Tier 4 smoke
9bbe1d5 prompts: s22 handoff updated — 6 of 6 verify corpora pass MVP gate
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Streamlit state at end of this session

Parser app launched in background (this session) on
`http://127.0.0.1:8501`:

```bash
BASIC_AUTH_USER=admin BASIC_AUTH_PASS=admin USE_TRACK_2=1 \
  .venv/bin/python -m streamlit run app.py \
  --server.address=127.0.0.1 --server.port=8501 \
  --server.headless=true --browser.gatherUsageStats=false
```

The venv was rebound via `python3 -m venv --upgrade .venv` (entry-point
scripts have stale shebangs from the `~/Downloads/` → `~/Documents/`
move; use `.venv/bin/python -m streamlit` instead of `.venv/bin/streamlit`).

If the user has restarted their machine, restart the server using the
command above before continuing trial step 1.

## Branch-stability guard

No new occurrences in s23 / s24. Eighth opportunity declined-by-default
since the user has shown no interest in worktree isolation. Continue
deferring.

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

## Out of scope for the next session

Unchanged from previous handoffs plus one new item:

- Don't edit Track 1 files.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Twenty-four
  Track 2 commits + fourteen handoffs** sitting local since 2026-05-11.
- **NEW: Don't edit the HTML renderer repo without explicit user
  approval** — that's a separate ship cadence and separate git history.

## Memory entries that should already be loaded

Two NEW entries written this session:

- `project_track2_html_pipeline.md` — the 4-stage pipeline ending at
  HTML, not JSON.
- `project_html_renderer_version_gap.md` — renderer on v6.3.3,
  engine on v6.3.5, degrades gracefully but loses fields.

Both are indexed in `MEMORY.md`.

## Suggested first action for the next session

**Ask the user what they have in hand.** Three branching paths:

1. **"I have all 3 engine JSONs + claude.ai analysis JSON ready"** →
   Boot the HTML renderer (Option 1), produce HTML, review.

2. **"I hit a blocker at step X"** → Debug (Option 2). Most likely the
   claude.ai context-limit scenario — fall back to the 2-step approach
   documented in Option 2.

3. **"I haven't run anything yet, want to do something else first"** →
   Pick from Option 4 (v0.2 prompt edits, cheap) or Option 5 (remaining
   Tier-4 smokes, evidence breadth) while the Huahub trial waits.

Whatever path: confirm `git status` + branch + test count BEFORE any
code work. Track 2 work happens only on `track-2-development`.
