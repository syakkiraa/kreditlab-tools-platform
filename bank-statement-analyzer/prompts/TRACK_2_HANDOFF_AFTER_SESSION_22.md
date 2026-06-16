# Track 2 handoff — picking up after session 22

State at end-of-session-22 (2026-05-15). Use this when starting a
fresh chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `f7b9a85`. One Track 2 code
commit landed in s22 (`f7b9a85`), preceded by the two s22 handoff
prompts commits (`62019c3`, `9bbe1d5`).

**Test count:** 911 / 911 (890 + 21 new from s22).

**One Track 2 code commit added in s22:**

| Commit | Files | Tests | Role |
|---|---|---|---|
| `f7b9a85` | `kredit_lab_classify_track2.py`, `tests/test_track2_company_root_numeric_prefix.py`, `tests/test_track2_report_info_rp_population.py` | +21 | Two engine fixes from the Tier-4 smoke audits — `_company_root()` numeric-prefix strip + `report_info.related_parties` population with schema-compliant objects |

## What session 22 accomplished

### Two Tier-4 smokes ran against `SYSTEM_PROMPT_TRACK2_v0_1.md` (v0.1)

**Smoke #1 — Principal Gas (Bank Islam, Aug-Dec 2025, 176 txns).**
Engine output at
[validation runs - json/Track 2 engine outputs/Track 2 Engine Output - Principal Gas (s21).json](../validation%20runs%20-%20json/Track%202%20engine%20outputs/Track%202%20Engine%20Output%20-%20Principal%20Gas%20%28s21%29.json).
Filled input at
[prompts/RUN_INPUT_FILLED_PRINCIPAL_GAS.md](RUN_INPUT_FILLED_PRINCIPAL_GAS.md).
Verdict: **STRONG PASS** on the v0.1 prompt. The AI followed scope
guards (no row-level reclassification, no MEDIUM-RP promotion, no
re-derived totals), produced both Deliverable 1 (analysis JSON) and
Deliverable 2 (parser quality report), and surfaced 3 real findings
plus 2 minor AI errors.

**Smoke #2 — Mazaa (Public Bank, Jan-Jun 2025, 497 txns).**
Engine output at
[validation runs - json/Track 2 engine outputs/Track 2 Engine Output - Mazaa (s21).json](../validation%20runs%20-%20json/Track%202%20engine%20outputs/Track%202%20Engine%20Output%20-%20Mazaa%20(s21).json).
Filled input at
[prompts/RUN_INPUT_FILLED_MAZAA.md](RUN_INPUT_FILLED_MAZAA.md).
Verdict: **VERY STRONG PASS**. Improved on Smoke #1 in three ways:
Flag #4 count math correct (1, not 5 — PG conflated #4 vs #9),
no date hallucinations, AND Deliverable 2 included a root-cause
diagnosis with proposed code-level fix for the own-party gap (the
numeric-prefix mismatch — exactly what s22's Fix #1 addresses).

### Engine fixes shipped in commit `f7b9a85`

**Fix #1 — `_company_root()` strips leading numeric prefix.** SSM-
registration-prefix names like `"010 MAZAA SDN BHD"` were producing
roots `"010 MAZAA"`, which failed substring match against descriptions
that only carry the public name (`"... MAZAA SDN BHD"`). Now produces
`"MAZAA"`. Alphanumeric leaders (`3M`, `1MDB`) preserved.
Implementation at
[kredit_lab_classify_track2.py:1727-1747](../kredit_lab_classify_track2.py#L1727-L1747).

Mazaa side-by-side post-fix:
- `total_own_party_cr` 0 → **RM 941,100.00** (captures all 55
  `DUITNOW TRSF CR ... MAZAA SDN BHD` rows + the 2 big June
  `RMT CR ... AT CPC MAZAA SDN. BHD.` rows + 2 other matches).
- `total_unclassified_cr` 1,137,592.94 → 196,492.94.
- T2 unclassified row count 456 → **1**.

**Fix #2 — `report_info.related_parties` populated with effective
list + schema-compliant objects.** Pre-fix the line at 5802 used the
*un-merged* `related_parties` arg, so analyst-supplied RPs surfaced
but auto-confirmed RP3 HIGH names did not. Now uses
`effective_related_parties` (merged) AND emits schema-required
`{name, relationship: "Affiliate"}` objects (the pre-fix code would
have emitted plain strings, which the v6.3.5 schema rejects — the
accidental `[]` was masking this).
Implementation at
[kredit_lab_classify_track2.py:5817-5828](../kredit_lab_classify_track2.py#L5817-L5828).

Principal Gas side-by-side post-fix surfaces:
- `MERCHANT STREET` — real auto-confirmed RP driving the RM 329K
  `total_related_party_dr`. This was the analyst-facing gap the AI
  flagged honestly as "Parties: (no canonical names provided)".
- (also `PRINCIPAL GAS (OWN-PARTY)` — a false-positive surfaced by the
  fix; see "New finding" below).

### Tests added (21)

Two new files, both follow the s21 single-concept-per-file pattern:

- [tests/test_track2_company_root_numeric_prefix.py](../tests/test_track2_company_root_numeric_prefix.py)
  — 15 cases: 9 direct unit tests on `_company_root`, 3 on
  `_own_party_match` end-to-end with numeric-prefix company names,
  3 orchestrator-level on a Mazaa-shaped fixture.
- [tests/test_track2_report_info_rp_population.py](../tests/test_track2_report_info_rp_population.py)
  — 6 cases: auto-confirmed-RP surfacing, analyst-supplied surfacing,
  case-insensitive dedup, no-RP-no-population baseline, default
  `Affiliate` relationship, and the RP-totals-vs-list invariant
  ("if `total_related_party_cr/dr > 0`, the list MUST be non-empty").

## New finding surfaced by s22's fixes (NOT introduced — pre-existing)

**The RP3 auto-confirm scanner promotes synthetic/rail-label bucket
names to HIGH-confidence alongside real RPs.** Pre-s22 this was
invisible because `report_info.related_parties` was always `[]`. Now
that the list is populated, the false positives are surfaced:

- **Principal Gas:** `PRINCIPAL GAS (OWN-PARTY)` appears as an
  Affiliate. This is the engine's synthetic OWN-party bucket label
  (built by the counterparty_ledger pipeline); the dispatcher
  correctly handles its rows as OWN, but the RP3 scanner also scores
  it as HIGH-confidence RP because it has all five behavioral signals
  (concentration, bidirectional, recurrence, etc.). Filter via
  `OWN_PARTY_MARKER_RE` at
  [kredit_lab_classify_track2.py:1692](../kredit_lab_classify_track2.py#L1692) — single-line
  addition to the exclude-prefix check in
  `scan_related_party_candidates` (currently `_RP_EXCLUDE_PREFIXES =
  ("UNIDENTIFIED", "UNNAMED")` at
  [kredit_lab_classify_track2.py:1819](../kredit_lab_classify_track2.py#L1819)).

- **Mazaa:** `TRSF DR` appears as an Affiliate (29 transactions, RM
  1.07M). This is the rail-label bucket that aggregates *every*
  DuitNow TRSF DR whose counterparty the parser couldn't extract — 29
  unrelated payments under one synthetic label. The scanner sees one
  high-volume "counterparty" and auto-confirms. Same underlying class
  of problem as #1 — the scanner shouldn't promote bucket-shape names.
  Fix path: extend `_RP_EXCLUDE_PREFIXES` with rail labels (`TRSF`,
  `RMT`, `DEP-ECP`, `DR-ECP`, `IBG`, `CHEQ`, etc.) OR add a separate
  rail-label-shape detector before scoring.

**Estimated cost for session 23:** 0.5-1 hour for the OWN-PARTY filter
+ rail-label exclude prefixes + ~6 unit tests (1 per excluded shape).

## Sync state vs main

Still 19+ commits behind main. Unchanged. Defer.

## Cumulative state across sessions 1-22

**Functions ported / built (78 total — 77 from s19/s20 + 0 new in
s21 + 1 modified in s22):** `_company_root()` modified to strip
leading numeric prefix; no new functions added. Test count is the
clearer signal: 911 / 911.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree still carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path. The s22 commit
followed this — only the three Track 2 paths were staged.

## Big-picture progress

22 sessions in. Engine feature-complete + s22 fixes. Tier 4 prompt
v0.1 validated against 2 of 6 verify corpora (Principal Gas, Mazaa);
both passed scope guards and produced both deliverables. **MVP ship
verdict: still GO.**

**Remaining to first analyst trial:**

| Slice | Sessions | Gates |
|---|---|---|
| RP3 scanner false-positive filter (OWN-PARTY + rail labels) | 0.5-1 | Optional but improves analyst-facing output |
| v0.2 prompt edits (3 small) | 0.5 | Cosmetic — `total_rm` typo, Flag #4 vs #9 disambiguation, scope-guard tightening if needed |
| App.py wire-through (USE_TRACK_2 flag) | 1 | Unblocks first internal Streamlit trial |

**Realistic remaining: 1-2 sessions to first analyst trial.**

## Open items the user can tackle next

(MVP gate already passed. The s22 fixes improve quality but were not
blocking ship.)

### Option 1 — RP3 scanner false-positive filter (Recommended)

Extend `_RP_EXCLUDE_PREFIXES` and/or add an `OWN_PARTY_MARKER_RE`
check in `scan_related_party_candidates` to drop:
- Any bucket name matching `OWN_PARTY_MARKER_RE` (synthetic
  own-party label).
- Rail-label-prefix buckets: `TRSF`, `RMT`, `DEP-ECP`, `DR-ECP`,
  `IBG `, `CHEQ`, etc.

Implementation site:
[kredit_lab_classify_track2.py:1819](../kredit_lab_classify_track2.py#L1819)
(extend the tuple) +
[kredit_lab_classify_track2.py:2041](../kredit_lab_classify_track2.py#L2041)
(extend the filter to also run `OWN_PARTY_MARKER_RE.search(upper)`).
Add 1 test per excluded shape. ~30-60 min.

After this fix, re-run the side-by-side on Principal Gas + Mazaa to
confirm `report_info.related_parties` contains only real names:

```bash
python scripts/track2_side_by_side.py \
  "validation runs - json/claude ai prompt file/Full Report Sample (April 2026 - pre-parser-fix baseline)/Full Report PBB Mazaa.json" \
  --out /tmp/track2_s23/mazaa

python scripts/track2_side_by_side.py \
  /tmp/track2_s21/principal_gas_full_report.json \
  --out /tmp/track2_s23/principal_gas
```

Expected: Mazaa drops `TRSF DR` from the RP list; Principal Gas
drops `PRINCIPAL GAS (OWN-PARTY)`, retains `MERCHANT STREET`.

### Option 2 — v0.2 prompt edits

Three small edits to
[prompts/SYSTEM_PROMPT_TRACK2_v0_1.md](SYSTEM_PROMPT_TRACK2_v0_1.md):

1. **§8 `total_rm` → `total_amount`** typo fix (line 285). The v6.3.5
   schema `$defs.party` uses `total_amount`; the AI ignored the typo
   and emitted `total_amount` on both smokes, so this is cosmetic but
   should land.

2. **§3.1 Flag #4 vs #9 disambiguation.** The Principal Gas AI
   conflated Flag #4 (High Value CR >3x EOD) with Flag #9 (Large
   Credits ≥RM100K), emitting "5 credits exceed 3x EOD totalling RM
   1,073,459.85" when the engine's `total_high_value_cr` is the
   single Sep-17 RM 1.07M txn. Add a sentence pointing each flag at
   its source consolidated field. The Mazaa AI got this right (1
   credit, RM 800K), so it's not load-bearing — but locking the rule
   prevents drift.

3. **§6 "dates and amounts must be copied verbatim"** hard rule. The
   PG AI hallucinated `02-Dec` for a `2025-12-31` row. Mazaa AI had
   no date errors, so again not load-bearing — defensive add.

~30 min total. Rename to v0.2 + bump §9 version line.

### Option 3 — Continue Tier-4 smoke across remaining 4 corpora

Felcra (Bank Rakyat), Waja (RHB), KMZ + Mytutor (BIMB) are the
remaining s21 verify corpora. Engine outputs at
`/tmp/track2_s21/{felcra,waja,kmz,mytutor}/track2.json` (volatile)
or build stable copies via:

```bash
for c in felcra waja kmz mytutor; do
  cp "/tmp/track2_s21/$c/track2.json" \
    "validation runs - json/Track 2 engine outputs/Track 2 Engine Output - ${c^} (s21).json"
done
```

Then prep `prompts/RUN_INPUT_FILLED_<NAME>.md` per the established
pattern (PG + Mazaa are the templates). 4 smokes × ~30 min interactive
= ~2 hours of analyst-side work; my time is ~5 min per filled-input
file. Gives v0.2 a 6-of-6 evidence base.

### Option 4 — App.py wire-through

`USE_TRACK_2` env var or sidebar toggle in `app.py` routing the
Streamlit UI to the Track 2 engine. ~1 session. Unblocks first
internal analyst trial of the full pipeline. The pre-analysis input
template flow (paste into chat) stays — wire-through is just the
parser → engine step.

### Blocked items (unchanged from s21)

- C12 deterministic FD/interest — no detector ported (lowest
  priority).
- CIMB AI_ASSIST — Tier 4 prompt territory; v0.1 covers generically.
- Principal Gas multi-bank consolidation — PGSB has 3 banks (Bank
  Islam, Maybank, CIMB); s21 only built the Bank Islam slice. Real
  analyst view needs all 3. Lower priority than #1/#2/#4 above.

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline c9c8d30..HEAD                 # should show 4 commits
python -m unittest discover tests 2>&1 | tail -5  # confirm 911 / 911
```

Expected output of the last command:
```
Ran 911 tests in 0.0XXs
OK
```

The `git log` should show (top-down, newest first):
```
<this-handoff-commit> prompts: Track 2 session-23 handoff (after session 22)
f7b9a85 Track 2 session 22: engine fixes #1 + #2 from Tier 4 smoke
9bbe1d5 prompts: s22 handoff updated — 6 of 6 verify corpora pass MVP gate
62019c3 prompts: Track 2 session-22 handoff (after session 21)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

No new occurrences in s22. Seventh recurrence was s13. Durable
mitigation: `git worktree add ../Bank-Statement-Track2
track-2-development`. User has declined seven times — only offer
again if it bites harder.

## Architecture rules (re-read before any code)

Unchanged from s21:

- Track 2 implements `CLASSIFICATION_RULES_v3_5.json` regex
  **verbatim**. When the parser emits a bank-specific shape that the
  LOCKED rule doesn't cover, lock it as a corpus-gap test — do NOT
  widen the Track 2 regex without updating v3.5 first.
- Track 1 (`kredit_lab_classify.py`, `SYSTEM_PROMPT_v3_5_6.md`) is
  **frozen**. Track 2 must not import from it. Track 2 fixes that
  diverge from Track 1 are fine *as long as the divergence is
  intentional and tested* — s22's `_company_root` numeric-prefix
  strip diverges from Track 1's identical implementation; that is the
  fix.
- Schema validation is the hard gate. `validate_track2_result()`
  must pass on every engine output. The s22 Fix #2 surfaced a
  schema-vs-code mismatch (related_parties shape) that pre-existed
  but was masked by the accidental `[]` — now corrected.

## Out of scope for the next session

Unchanged from previous handoffs:

- Don't edit Track 1 files.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Twenty-two
  Track 2 commits** + thirteen handoffs sitting local since
  2026-05-11.

## Memory entries that should already be loaded

Unchanged from previous handoff. No new memory entries needed — s22
is fully captured in this handoff + the f7b9a85 commit message + the
21 test docstrings.

## Suggested first action for the next session

**Option 1 (RP3 false-positive filter) is the highest-ROI follow-up
to s22.** It directly closes the loop on the only new finding s22's
fixes surfaced. ~0.5-1 hour total, ships with tests, unblocks cleaner
Tier-4 smoke output for the remaining 4 corpora.

After Option 1: pick **Option 4 (app.py wire-through)** as the
session that unlocks the first internal analyst trial. v0.2 prompt
edits (Option 2) can ride along in any later session — they're
cosmetic.
