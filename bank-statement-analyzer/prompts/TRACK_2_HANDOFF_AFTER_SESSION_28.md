# Track 2 handoff — picking up after session 28

State at end-of-session-28 (2026-05-18). Single-focus session: shipped
Pattern B L5 (the trailing-uppercase fallback the s27 handoff teed up),
closing the Huahub trial entirely.

**Read first:**
1. `~/.claude/projects/.../memory/project_huahub_trial_bugs.md` — now
   lists all 6 fixed bugs; trial fully resolved.
2. `prompts/TRACK_2_HANDOFF_AFTER_SESSION_27.md` — predecessor; the
   Pattern B L1+L2+L3 implementation L5 extends.
3. `~/.claude/projects/.../memory/feedback_audit_claude_misdiagnosis.md`
   — Pattern 3 (sub-agent loose-regex FP) still applies; the 18K cross-
   bank audit template L5 used is the canonical mitigation.

## What landed in s28

One engine commit. **Local — not pushed.** Per the standing rule, no
push or merge to either repo's `main` without explicit user approval.

| # | Commit | Repo / Branch | Effect |
|---|---|---|---|
| 1 | `0dd21a0` | engine / `track-2-development` | **Track 2 engine: Pattern B L5 trailing-uppercase fallback.** Adds `_extract_trailing_uppercase` + `_L5_*` constants in `kredit_lab_classify_track2.py`. Wired in as the (c) branch of `_extract_after_rail_label_prefix` — runs only when L2 confirms a known rail-label prefix and BOTH paren/corp-suffix anchors fail. 8 new tests + 3 replaced tests (the s27 "no-anchor passthrough" tests whose preconditions L5 broke). |

**Test suite:** 993 → 1000 (+7 net new green).

**Memory updates this session:**
- `project_huahub_trial_bugs.md` — bug #6 entry added (L5 fix); name/
  description updated to "RESOLVED s26+s27+s28".
- `MEMORY.md` — Huahub trial index line refreshed.

## L5 design summary (for the next reader)

After L2 confirms a known rail-label prefix matched and both anchor
patterns (`_PAREN_ANCHOR_RE`, `_CORP_SUFFIX_ANCHOR_RE`) failed, L5:

1. Strips trailing `[\d\s_]+` noise from the remainder.
2. Tokenises on whitespace.
3. Walks right-to-left, collecting consecutive UPPERCASE tokens
   (`^[A-Z][A-Z&/\-]*$`) up to `_L5_MAX_TOKENS=5`.
4. Stops at the first non-uppercase or digit-bearing token.
5. Drops leading + trailing stop-word tokens from the captured run
   (`_L5_STOP_WORDS`: PAYMENT/INVOICE/TRANSFER/months/connectives).
6. Requires `>= _L5_MIN_KEPT=2` non-stop-word tokens AND total
   length `>= 4` chars; else returns None (pass-through).

**Cross-bank FP surface = the rail-label gate.** L5 cannot fire on
non-rail-label-prefixed names. Adding new rail-label prefixes to
`_RAIL_LABEL_PREFIX_RE` requires re-running the 18K-corpus audit (see
"Audit template" below).

## Cross-bank audit results (s28)

71 JSONs across `validation runs - json/` + `Track 2 Files/`, 18,786
unique counterparty names:

| Layer set | Names changed | Bank concentration |
|-----------|---------------|--------------------|
| Pattern A alone (pre-s27) | 5 | INTEREST cleanups, cross-bank |
| Pattern A + Pattern B L1+L2+L3 (s27) | 17 | 5 + 12 Huahub-only |
| Pattern A + Pattern B L1+L2+L3+L5 (s28) | 39 | 17 + 22 Huahub-only |

**Zero accidental matches on legitimate non-rail-label names anywhere
in the corpus.** All 22 L5 firings are the expected Huahub HLB rail-
label-prefixed entries (AEON CO ×11, BEMED TEMPUA ×2, F IMAN FARMASI
IMAN ×2 + 1 partial, PASTEL CARE, CITY PHARMACY, MEDWISE PHARMACY,
SAR CARE CONSTRUCT, BESTARI HEALTH CARE).

## Huahub ledger impact (simulated post-L5)

Applied `clean_counterparty_name` + a fingerprint-based dedup to the 3
fresh s27 per-bank engine JSONs in `Track 2 Files/Huahub Tarack 2/`:

| Bank | Pre-L5 (post-s27) | Post-L5 (simulated) | Delta |
|------|-------------------|---------------------|-------|
| HLB  | 177 | 159 | -18 (-10.2%) |
| CIMB |  15 |  14 | -1 |
| MBB  |  36 |  36 | unchanged |

Combined post-s26+s27+s28 Huahub: **232 → 209 entries (-23, -9.9%)**.

The L5 simulation is in-memory; the authoritative number requires a
re-run of the 3 per-bank Streamlit sessions under `USE_TRACK_2=1`.
Optional verification — current numbers are close enough to ship.

## Known limitation (locked in test)

`CR ADV-INTERBANK GIRO AT KLM 660 53 7 6 F IMAN 3 FARMASI IMAN 0 0`
extracts to `FARMASI IMAN` (not `F IMAN FARMASI IMAN`) because the
mid-string digit `3` stops L5's right-to-left walk. So the 1 entry
sits in a separate bucket from the 2 other `F IMAN FARMASI IMAN`
occurrences. Output is still ~85% shorter than the 56-char raw
narrative. Locked in `test_l5_known_limitation_mid_string_digit_truncates`.

Future work that wants to merge these properly would need either:
- An L7+ layer allowing a single digit-token interruption inside the
  trailing run, or
- A second-pass canonicalisation step that fuzzy-matches cleaned names
  by token overlap.

Both have higher cross-bank FP risk than the current strict-consecutive
strategy. Not in scope for the Huahub trial close-out.

## What still needs to ship

The Huahub trial is **fully resolved**. The remaining Track 2 work
streams are independent of Huahub-specific bugs:

### Renderer schema sync v6.3.3 → v6.3.5 (separate repo)

`bank-statement-analysis-HTML-fresh/` is on `renderer-v6.3.5-support`
at `4244275` (post-revert). No push or merge to renderer `main` without
explicit user approval. Sync is its own 1-2 session workstream — the
renderer is currently warn-and-degrade on schema v6.3.5 engine output.

The post-Pattern B Huahub HLB ledger (159 entries down from 177) is
ready to render end-to-end whenever the user wants to verify visually.

### Ship-readiness lever per `project_ship_ready_strategy.md`

Strategy memo says "engine ~6-8 sessions away" with V3-B Auto-RP Step
2 as the biggest single rate-variance lever. Re-read the strategy memo
before locking the next engine session's scope.

### User action — optional verification

If you want authoritative numbers (not in-memory simulation) for the
Huahub ledger reductions, re-run the 3 per-bank Streamlit sessions
under `USE_TRACK_2=1` and drop the fresh JSONs into
`Track 2 Files/Huahub Tarack 2/`. Expected:
- HLB: 159 counterparties (was 177)
- CIMB: 14 counterparties (was 15)
- MBB: 36 counterparties (unchanged)

The reconciliation numbers and salary-month counts should match s27's
post-fix measurements (0/24 FAIL months, 4 HLB salary months).

## Audit template (for any future Pattern B layer / new rail-label prefix)

The cross-bank audit script L5 used (inline, not yet a repo script):

```python
from __future__ import annotations
import json, os, glob
from kredit_lab_classify_track2 import clean_counterparty_name

roots = ["validation runs - json", "Track 2 Files"]
files = []
for r in roots:
    files.extend(glob.glob(os.path.join(r, "**", "*.json"), recursive=True))

unique_names = set()
def walk(obj):
    if isinstance(obj, dict):
        nm = obj.get("counterparty_name")
        if isinstance(nm, str) and nm: unique_names.add(nm)
        for v in obj.values(): walk(v)
    elif isinstance(obj, list):
        for v in obj: walk(v)
for path in files:
    try:
        with open(path) as f: d = json.load(f)
    except Exception: continue
    walk(d)

for nm in sorted(unique_names):
    cleaned = clean_counterparty_name(nm)
    if isinstance(cleaned, str) and cleaned != nm:
        print(f"{nm!r} -> {cleaned!r}")
```

Expected output post-s28 = 39 names changed. Any new change set after
adding rules MUST be inspected name-by-name; legitimate-looking names
(no rail-label prefix, no special-bucket lead-in) appearing in the
diff is the canary signal that the new rule is too loose.

## Out-of-scope (unchanged from s27)

- Don't edit Track 1 files (`kredit_lab_classify.py`, `app.py`, `SYSTEM_PROMPT_v3_5_6.md`).
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't push to origin (parser or renderer) without explicit user approval.
- Don't merge `renderer-v6.3.5-support` to renderer `main` until user signs off.
- Don't initiate parser or `core_utils` edits without explicit user approval.
- Don't attempt the main → track-2-development merge unless explicitly scoped as a sync session.
- Don't fix classification/analysis issues in the renderer.
- Before acting on any audit's fix list, run parser → engine reconciliation across the full corpus per flagged bank.

## First commands the next session should run

```bash
git status --short                                              # confirm known-dirty matches s27 state + 1 new commit
git branch --show-current                                       # MUST be track-2-development
git log --oneline 13a06ea..HEAD | head                          # should show 0dd21a0 + this handoff
python -m unittest discover tests 2>&1 | tail -5                # confirm 1000 / 1000
git -C bank-statement-analysis-HTML-fresh branch --show-current # should be renderer-v6.3.5-support
git -C bank-statement-analysis-HTML-fresh log -1 --oneline      # should show 4244275
```

If any don't match → stop and investigate.

## Suggested first action for the next session

Two reasonable paths, the Huahub trial having closed:

1. **Renderer schema sync v6.3.3 → v6.3.5** (own repo): Switch to
   `bank-statement-analysis-HTML-fresh/`, sync schema, ship the
   v6.3.5 support to renderer `main` (after the user signs off on the
   `acd6112` revert and the Pattern B output rendering correctly).
   1-2 sessions; bumps renderer past warn-and-degrade state and
   unblocks analyst-facing improvements.

2. **Ship-readiness lever per `project_ship_ready_strategy.md`**: Memo
   says "engine ~6-8 sessions away" with V3-B Auto-RP Step 2 as the
   biggest single rate-variance lever. Re-read the strategy memo to
   lock the next engine session's scope.

Path 1 unblocks analyst delivery of the Huahub trial output. Path 2
progresses MVP. User decides.

Whatever path: confirm `git status` + branch + test count BEFORE any
code work. Track 2 work happens only on `track-2-development`.
