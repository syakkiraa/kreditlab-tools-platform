# Track 2 handoff — picking up after session 31

State at end-of-session-31 (2026-05-21). One renderer commit shipped
locally on `renderer-v6.3.5-support`, plus a ship-ready scope reset:
Affin OCR and V3-B Auto-RP SDK are now **explicitly out of the
ship-ready milestone** (not just deferred). Realistic remaining: 1-3
working sessions to "stabilize the rest" + a separate auth scope
decision.

**Read first:**
1. `~/.claude/projects/.../memory/project_ship_ready_strategy.md` —
   **REWRITTEN s31.** Finish line redefined; Affin + V3-B SDK
   explicitly out of scope. Read the punch-list tables at the bottom.
2. `~/.claude/projects/.../memory/feedback_renderer_vs_classifier.md` —
   the hard rule that drove the s31 renderer additions to be
   presentation-only, never masking engine bugs. Standing rule.
3. `~/.claude/projects/.../memory/project_html_renderer_version_gap.md` —
   **REWRITTEN s31** to reflect what's actually rendered now
   (subthreshold + channel-blind + extraction_stats) and what's still
   deferred (account_type_determination — waits for parser-meta
   threading).
4. `~/.claude/projects/.../memory/feedback_no_sdk_until_bank_deploy.md` —
   s31 update added: V3-B SDK is now out of scope, not just waiting on
   stability. Do not propose SDK work until explicit user unblock.
5. `~/.claude/projects/.../memory/project_affin_ocr_deferred.md` —
   s31 update: Affin OCR out of scope. Do not propose Affin work until
   explicit user unblock.
6. `prompts/TRACK_2_HANDOFF_AFTER_SESSION_30.md` — predecessor.

## What landed in s31

One renderer commit, on the renderer repo's `renderer-v6.3.5-support`
branch. **Local — not pushed; not merged to renderer `main`.** Standing
rule: no push or merge to either repo's `main` without explicit user
approval.

| # | Commit | Repo / branch | Effect |
|---|---|---|---|
| 1 | `652099a` | `bank-statement-analysis-HTML-fresh/` on `renderer-v6.3.5-support` | **Surface 3 v6.3.5 engine fields the renderer was silently dropping.** Pure presentation per `feedback_renderer_vs_classifier.md`. (a) `consolidated.statutory_compliance.subthreshold_employer` → "Sub-threshold employer check" card in new "Employer Footprint Checks" sub-section under Statutory Compliance; badge OK/SUB-THRESHOLD + amounts + engine `reason` verbatim. (b) `consolidated.statutory_compliance.channel_blind_employer` → companion card; badge OK/CHANNEL-BLIND + cheque-DR/gross-DR/ratio + thresholds + engine `reason` verbatim. (c) `counterparty_ledger.extraction_stats` → cards in ledger summary-grid, shape-polymorphic (single-bank: pattern_matched/special_bucket/raw_fallback; multi-bank consolidated: merged_from_banks). Cards hidden when source field absent/zero. +61/-1 in `app.py`. |

**Deferred (s31):** `accounts[].account_type_determination`. Every
current Track 2 output has `confidence=LOW + locked_rationale="Track 2
default — parser meta not threaded"`. Rendering it would print the
same noise on every account card. Revisit after parser-meta threading
lands (no current session scoped for that — it's not on the in-scope
punch list).

**Renderer branch state:** `renderer-v6.3.5-support` is now **3
commits ahead of renderer `main`** (`acd6112`, `4244275`, `652099a`).
Merge to renderer `main` is gated on user sign-off after visual
spot-check of `/tmp/renderer_smoke/{huahub,mazaa,upell,mtc}.html`
(written during s31 smoke test — may have been cleaned up on reboot;
regenerate by re-running the smoke-test block at the end of this
handoff if needed).

**Parser repo state:** unchanged from s30. Still on
`track-2-development`, HEAD = `621b57b`, s30 commits `7fde7c2` +
`cce8e61` still local-only. Test suite 1040/1040 (6 regression
skipped). No parser/engine work happened in s31.

**Memory updates this session:**
- `project_ship_ready_strategy.md` — **rewritten**; ship-ready scope
  reset; new "in scope" + "out of scope" punch-list tables at bottom
- `project_html_renderer_version_gap.md` — **rewritten**; reflects
  v6.3.5 fields now rendered + what's deferred + smoke-test method
- `project_affin_ocr_deferred.md` — status upgraded to "deferred AND
  out of ship-ready scope"
- `feedback_no_sdk_until_bank_deploy.md` — s31 update: SDK out of
  scope, not just waiting for stability
- `MEMORY.md` — index entries refreshed (ship-ready, renderer, Affin,
  SDK)

## Where we are on the ship-ready line

**Pre-s31 estimate:** ~3-5 sessions remaining.
**Post-s31 (after scope reset):** **1-3 sessions** remaining in
ship-ready scope + separate auth scope decision.

**In-scope ship-ready punch list:**

| Item | Sessions | Status |
|---|---|---|
| Renderer merge to renderer `main` + push | ~0.25 | gated on user spot-check + sign-off of `/tmp/renderer_smoke/*.html` |
| Keyword loop CP1–CP11 | 1-2 | not started; `CLASSIFICATION_RULES_v3_5.json` only; cross-bank PDF verification per `feedback_source_file_ceiling.md` |
| Bank Rakyat residuals + Cash Line triage | 0-1 | diagnostic; 76 unclassified rows on Felcra post-s30, mostly C26 natural-person ceiling; ship rule packs only with source-text evidence |
| Auth / multi-tenant | TBD | gated by undecided selling-motion (design-partner vs SaaS) — separate decision before scoping |

**Explicitly OUT of ship-ready scope (per user 2026-05-21 s31):**

| Item | Re-trigger |
|---|---|
| Affin OCR | user explicit unblock + tesseract install OR Railway prod sample (see `project_affin_ocr_deferred.md`) |
| V3-B Auto-RP Step 2 SDK | user explicit unblock + claude.ai web workflow stable (see `feedback_no_sdk_until_bank_deploy.md`) |

**Items already closed (cumulative):**
- ~~#2 Cheap classifier wins~~ (s30, commits `cce8e61` + `7fde7c2`)
- ~~#3 Bank Rakyat DATAPOS edge cases~~ (s30, part of `7fde7c2`)
- ~~#4 Regression suite~~ (s29, commit `1cdfe82`)
- ~~#5 Mytutor per-business-type rule~~ (s30, verified ceiling — no
  code change appropriate)
- ~~Renderer schema sync v6.3.3 → v6.3.5 (field rendering)~~ (s31,
  commit `652099a` — still needs merge to main)

## Out-of-scope (unchanged + s31 additions)

Standing rules carried forward from prior handoffs:
- Don't edit Track 1 files (`kredit_lab_classify.py`, `app.py` in repo
  root, `SYSTEM_PROMPT_v3_5_6.md`) without explicit user approval.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser or renderer) without explicit user
  approval.
- Don't merge `renderer-v6.3.5-support` to renderer `main` until user
  signs off.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → `track-2-development` merge unless
  explicitly scoped as a sync session.
- Don't fix classification/analysis issues in the renderer
  (`feedback_renderer_vs_classifier.md`).
- Before acting on any quality-report / audit / "missed keywords"
  finding, verify against raw PDF text first per
  `feedback_source_file_ceiling.md`. Source-file ceilings are not
  bugs to fix.
- Don't start Affin OCR work without the gate in
  `project_affin_ocr_deferred.md` being satisfied.

**NEW s31 (scope discipline):**
- **Affin OCR is OUT of ship-ready scope.** Do not include it in
  session planning, prioritization tables, or "what's next" suggestions
  unless the user explicitly unblocks it. The deferral memo is now
  also a scope memo.
- **V3-B Auto-RP Step 2 SDK is OUT of ship-ready scope.** Same rule
  as Affin: don't surface it as a candidate next-session item until
  explicit user unblock. Even if claude.ai web workflow stabilizes,
  the scope reset stands; user must explicitly re-open.

## First commands the next session should run

```bash
git status --short                                              # confirm known-dirty matches state
git branch --show-current                                       # MUST be track-2-development
git log --oneline 3acd5cf..HEAD | head                          # should show 621b57b + 7fde7c2 + cce8e61
python -m unittest discover tests 2>&1 | tail -5                # confirm 1040 / 1040 (6 skipped)
RUN_REGRESSION=1 python -m unittest tests.regression.test_snapshots 2>&1 | tail -3  # optional: 6/6 green (~72s)
git -C bank-statement-analysis-HTML-fresh branch --show-current # should be renderer-v6.3.5-support
git -C bank-statement-analysis-HTML-fresh log -1 --oneline      # should show 652099a
git -C bank-statement-analysis-HTML-fresh log main..HEAD --oneline  # should show 3 commits: 652099a, 4244275, acd6112
```

If any don't match → stop and investigate.

## Suggested first action for the next session

The session should branch based on whether the user has spot-checked
`/tmp/renderer_smoke/*.html` (or the equivalent re-render) and
approved the visual:

### Path A — user approves renderer visual

**1. Merge `renderer-v6.3.5-support` → renderer `main`** (~0.25
session, gated on user explicit "merge" instruction):
```bash
git -C bank-statement-analysis-HTML-fresh checkout main
git -C bank-statement-analysis-HTML-fresh merge --ff-only renderer-v6.3.5-support
# Push only on explicit user instruction
```
Per `feedback_auto_merge_solo.md` this is fine to fast-forward locally;
push is the gated step.

**2. Move to keyword loop CP1–CP11** in the same session if budget
allows, otherwise stop and let the user decide. Workflow:
`prompts/improve_keywords.md`. Touches **only**
`validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`
(plus its v3_5_6 successor if that's what's now in use — confirm at
session start). Each keyword: pull cross-bank PDF samples, propose,
validate against multiple corpora per `feedback_crossbank.md`, commit
or skip per keyword. Don't add bank-specific keywords (memory rule).

### Path B — user has not yet approved renderer visual

Re-render the smoke samples first so user can spot-check:
```bash
cd "bank-statement-analysis-HTML-fresh"
python - <<'PY'
import json, sys, os, types
sys.path.insert(0, '.')
os.environ['BASIC_AUTH_USER']='x'; os.environ['BASIC_AUTH_PASS']='y'
st = types.ModuleType('streamlit')
class _Ctx:
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def __call__(self,*a,**k): return self
    def __iter__(self): return iter([_Ctx(),_Ctx(),_Ctx()])
    def __getattr__(self,n): return _Ctx()
def _cols(spec,*a,**k):
    n=len(spec) if hasattr(spec,'__len__') else int(spec); return tuple(_Ctx() for _ in range(n))
def _tabs(labels,*a,**k): return tuple(_Ctx() for _ in labels)
for n in ['set_page_config','title','markdown','warning','error','info','success','code','json','write','header','subheader','caption','text','dataframe','table','image','download_button','file_uploader','button','stop','sidebar','expander','spinner','progress','toggle','radio','checkbox','selectbox','text_input','text_area','number_input','metric','divider','empty','container']:
    setattr(st,n,_Ctx())
st.columns=_cols; st.tabs=_tabs
st.cache_data=lambda *a,**k:((lambda f:f) if not (a and callable(a[0])) else a[0])
st.cache_resource=st.cache_data
st.session_state={'logged_in':True,'username':'x'}
st.stop=lambda:(_ for _ in ()).throw(SystemExit(0))
sys.modules['streamlit']=st
import importlib.util
spec=importlib.util.spec_from_file_location('renderer_app','app.py')
mod=importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(mod)
except SystemExit: pass

BASE='../Track 2 Files/'
OUT='/tmp/renderer_smoke/'
os.makedirs(OUT,exist_ok=True)
for src,dst in [
    (BASE+'Huahub Tarack 2/huahub_consolidated_analysis.json', OUT+'huahub.html'),
    (BASE+'track2_mazaa.json', OUT+'mazaa.html'),
    (BASE+'track2_upell.json', OUT+'upell.html'),
    (BASE+'track 2 mtc.json', OUT+'mtc.html'),
]:
    with open(src) as f: data=json.load(f)
    data=mod.normalize_claude_v635(data)
    html=mod.generate_interactive_html(data)
    with open(dst,'w',encoding='utf-8') as f: f.write(html)
    print(f'{dst}  {len(html):,} bytes')
PY
```
Then ask user to inspect:
- `/tmp/renderer_smoke/huahub.html` → scroll to **Statutory Compliance**
  → confirm "Employer Footprint Checks" sub-section appears with
  Sub-threshold (green OK) + Channel-blind (amber CHANNEL-BLIND) cards;
  scroll to **Counterparty Ledger** → confirm "Merged from banks:
  CIMB, HLB, MBB" card.
- `/tmp/renderer_smoke/mtc.html` → confirm Pattern matched / Special
  bucket / Raw fallback cards under Counterparty Ledger.

Then proceed to Path A on approval, or revise per feedback if not.

### Path C — user picks something else

Acceptable alternatives within the in-scope punch list:

- **BR residuals + Cash Line deep-dive.** 76 unclassified rows on
  Felcra after s30. Triage: how many are natural-person C26 ceiling vs
  real extractable signal? Spot-check Cash Line corpus (BR/1) too.
  Don't ship rule packs without source-text verification per
  `feedback_source_file_ceiling.md`.
- **Auth/multi-tenant scoping conversation.** Not a code session —
  walk through the selling-motion decision (design-partner pilot vs
  self-serve SaaS) to unblock the auth-scope decision that's been
  sitting open.

Items the user might mention but should be **declined** unless they
explicitly unblock:

- Affin OCR — out of scope per s31 (`project_affin_ocr_deferred.md`).
- V3-B Auto-RP SDK — out of scope per s31
  (`feedback_no_sdk_until_bank_deploy.md`).

Whatever path: confirm `git status` + branch + test count BEFORE
any code work. Track 2 work happens only on `track-2-development`;
renderer work happens only on `renderer-v6.3.5-support` (or `main`
after merge approval).
