# HUAHUB Parser-Quality Bug Fixes — Handover (2026-05-12, final)

One-line summary: four HIGH-severity findings flagged across two HUAHUB
parser-quality audit rounds have been closed out. Three real bugs are
shipped to `main`; one was auditor invention (re-classified per spec, no
code change). The parser quality report prompt itself was patched to
stop the auditor-invention pattern in future runs.

---

## Status

| Bug | Description | Status | Commit |
|---|---|---|---|
| BUG-005 | Maybank Oct'25 opening off by RM 8,582.30 | **SHIPPED** | `b023d7b` |
| BUG-001 (orig) | CIMB `monthly_summary[].month` off-by-one on all 12 CIMB months | **SHIPPED** | `d558e4e` |
| BUG-002 | Counterparty `(MAYBANK ISLAMIC)` corrupted to `AYBANK ISLAMIC)` (45 tx / RM 3.24M) | **SHIPPED** | `f9d1377` |
| BUG-001 (new audit) | CIMB 8007569504 locked UNDETERMINED | **DROPPED** — auditor invention, not in spec | — |
| LIM-001 | HLB counterparty extraction (~191 rows, classifier already recovers) | **DEFERRED** | — |
| LIM-002 | MBB CR-side `TRANSFER TO A/C [SENDER]` label | **N/A** — bank-side convention | — |

All shipped commits live on `origin/main`. Railway deploys from `main`.

---

## What was wrong (and what we fixed)

### BUG-005 — Maybank Oct opening RM 8,582.30 delta — SHIPPED

NOT in `maybank.py`. The bank parser correctly extracted
`Beginning Balance 463,485.73DR` and emitted a synthetic
`description="OPENING BALANCE", balance=-463485.73, is_opening_balance=true`.

The bug was in `app.py:calculate_monthly_summary` — the first-month opening
seeder only recognised `"BEGINNING BALANCE"`. Maybank's synthetic row uses
`"OPENING BALANCE"`. String mismatch → `seed_opening` stayed `None` → fell
through to a fallback formula encoding Alliance's positive-debt-magnitude
OD convention but Maybank uses pre-negated → opening came out off by
exactly `2 × net_change` = RM 8,582.30.

Fix (commit `b023d7b`): regex now matches both `BEGINNING BALANCE` and
`OPENING BALANCE`. Maybank's authoritative value is honoured; the fallback
formula no longer fires for Maybank.

Verified by the 2026-05-11 re-audit: all 6 MBB monthly trails reconcile
delta = 0.00.

### BUG-001 (original) — CIMB month off-by-one — SHIPPED

`extract_cimb_statement_totals` at `app.py:608` deliberately applied
`_prev_month()` to the matched Statement Date. The original author assumed
CIMB's "Statement Date / Tarikh Penyata" was an *issue date* (day after
period end). Actual CIMB convention: the period-end date itself
(e.g. `31/10/2025` for the October statement). Rolling back one month
produced an off-by-one tag on every CIMB month.

Fix (commit `d558e4e`), defence in depth:
1. Drop the `_prev_month` rollback in the extractor. Use matched month directly.
2. In `calculate_monthly_summary` (CIMB-only branch), override the month
   with the dominant transaction-date month when transactions exist.
   Statement Date is the fallback only for zero-tx months.

Verified by the 2026-05-11 re-audit: all 12 HUAHUB CIMB PDFs produce a
`statement_month` matching the filename and the dominant transaction month.

### BUG-002 — counterparty `(MAYBANK ISLAMIC)` → `AYBANK ISLAMIC)` — SHIPPED

NOT in `maybank.py`. The bank parser correctly emits the description
`"BA SETTLEMENT (Maybank Islamic)"` (see `maybank.py:24 BA_SETTLEMENT_LABEL`).
The corruption happens in the shared counterparty-normalisation layer at
`app.py:4297`. The Malaysia-marker regex
`\((?:SARAWAK|SABAH|MALAYSI[A]?|SAR|L|M)\)?` matches its `M` alternative
anywhere — including inside `(MAYBANK ISLAMIC)`. The opening `(M` is
consumed even though it's mid-word.

Fix (commit `f9d1377`): add `\b` after the alternation so the single-letter
location tokens (L, M) only match when followed by a word boundary.
Verified against 10 representative inputs:

| Input | Old result | Fixed result |
|---|---|---|
| `(MAYBANK ISLAMIC)` | ` AYBANK ISLAMIC)` (bug) | `(MAYBANK ISLAMIC)` (preserved) |
| `(MAYBANK` truncated | ` AYBANK` (bug) | `(MAYBANK` (preserved) |
| `(M)` | strip | strip |
| `(M` truncated | strip | strip |
| `(SARAWAK)` | strip | strip |
| `(SARAWAK` truncated | strip | strip |
| `(MALAYSIA)` | strip | strip |
| `(MALAYSI` truncated | strip | strip |
| `(L)` | strip | strip |
| `(SAR)` | strip | strip |

Impact: 45 BA SETTLEMENT rows totalling RM 3.24M now display correctly in
`counterparty_ledger` and `top_payees`. Classification was already correct
(rule fires on `BA SETTLEMENT` prefix); the bucket name was the only
analyst-visible corruption.

### BUG-001 (new audit, CIMB 8007569504 UNDETERMINED) — DROPPED, not a real bug

The 2026-05-11 audit flagged this as HIGH severity because the parser
locked the account `UNDETERMINED` with LOW confidence while the classifier
resolved it to `CR` HIGH via month-aggregate reconciliation across 6 PDFs.

Per the parser quality report spec, this is not a parser bug:
1. Account-type-lock confidence is not in audit checks A-F.
2. The parser is being defensive — refusing to lock CR/OD when single-statement
   row-level evidence is inconclusive. That's correct "Flag, don't invent"
   behaviour, not a bug.
3. The classifier already resolves it; analyst's final output is correct
   (CR / Current Account / HIGH confidence).
4. Pushing month-aggregate logic into the parser is a scope expansion — a
   single-statement parser can't see its 5 siblings.

No code change. The patched spec (next section) prevents this item from
appearing in future reports.

### LIM-001 — HLB description-format counterparty extraction — DEFERRED

Real per spec: parser leaves `counterparty=None` on ~191 Hong Leong rows
where the beneficiary name IS in the description (between amount + purpose
and the trailing `20YYMMDDHLBB...` reference token).

Final analyst output is correct — the classifier extracts these names via
regex post-hoc (visible in `counterparty_ledger`: ERA VISION SUPPLY,
AEON CO, KOK KEONG DIAS, TELUS BAYU, KLASIK ALFA all populated correctly).

If/when prioritised, this is `missing_bank_patterns[]` work, NOT `bugs[]`.
HLB has at least four description formats (`CIB Instant Transfer at DIO`,
`Instant Transfer at KLM`, `Fund Transfer at DIO`, `Cr Adv-Interbank GIRO
at KLM`). Each needs a regex with examples. Tackle as a focused session
with a corpus survey first.

---

## Parser quality report prompt — PATCHED

The 2026-05-11 audit flagged BUG-001-new, OBS-001 (cross-file metadata
bleed), and OBS-002 (payroll cadence) — none of which fit the spec's six
audit categories (A balance, B description, C counterparty, D direction,
E date, F ledger). It also put LIM-001 in a non-spec `limitations[]` key
instead of the spec's `missing_bank_patterns[]`.

This is a recurring auditor pattern: invent audit dimensions outside the
spec, mis-bucket genuine findings, blame the parser when the classifier
already handles the case. Patching the prompt prevents it going forward.

**Patch location:** `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`
(new section "Verification gate before adding to `bugs[]`" between
"Grading Criteria" and "Parser Quality Report Structure").

**Five-point gate.** Before any item goes into `bugs[]`, the auditor must
confirm:
1. Item maps to one of audit categories A-F. Else drop or propose a new check.
2. Native-PDF citation: quote PDF text + show parser-emitted vs PDF-actual side by side.
3. Final-output gate: if the classifier silently corrects it, max severity
   MEDIUM and the bucket is `cleaning_limitations[]`, not `bugs[]`.
4. Defensive ≠ buggy: parser marking LOW/UNDETERMINED on inconclusive
   single-statement evidence is correct "Flag, don't invent" behaviour.
5. Correct output bucket: missing patterns → `missing_bank_patterns[]`;
   bank-side label conventions → `cleaning_limitations[]`; never `bugs[]`.

Working-tree change at session close — not yet committed.

---

## Expected delta if HUAHUB is re-run with the patched prompt

(Not required to close this work — the parser fixes are independently
verifiable from balance trails in the next pipeline run. Listed here so
future-you can sanity-check the patched prompt before relying on it for
a new entity.)

- BUG-002 disappears (fix live, ledger clean).
- BUG-001 (new) drops entirely (gates 1 + 4).
- LIM-001 moves into `missing_bank_patterns[]` with regex + examples.
- LIM-002 stays in `cleaning_limitations[]` (already correct).
- OBS-001 drops (gate 1, run-builder concern not parser).
- OBS-002 drops (gate 1, client observation not parser).
- Grade: A (24/24 trails PASS, pattern match 100%, zero `bugs[]`, one
  `missing_bank_patterns[]` entry for HLB).

---

## Critical context for next chat

1. **AI auditor (claude.ai web manual flow) has two bias patterns:**
   - **Mis-attribution** — blames the parser when the bug is in `app.py`
     shared utilities or in run-builder logic. Three examples in this
     run: BUG-005 originally attributed to `maybank.py` (was `app.py`),
     BUG-002 originally diagnosed as "MBA SETTLEMENT should be the form"
     (false — `BA SETTLEMENT` = Banker's Acceptance Settlement, complete
     on its own), OBS-001 framed as parser-side (was run-builder).
   - **Category creep** — invents audit dimensions outside the spec and
     flags items as HIGH bugs that don't fit any of the six audit checks.
     The patched gate addresses this directly.

   Verification recipe before accepting an auditor finding: cross-check
   against (a) parser raw output, (b) `pdf_integrity.arithmetic`,
   (c) re-derivation from `closing − credits + debits`, (d) which
   file/layer the field actually originates in. If two or more sources
   agree but the auditor's chosen field disagrees, the bug is in
   whatever produced the disagreeing field — often NOT the bank parser.

2. **Architecture reminder (Track 1 vs Track 2):**
   - Track 1 (`app.py`, bank parser modules) is the production code Railway
     deploys from `main`. Frozen for net-totals schema since 2026-05-01 but
     still receives bug fixes (BUG-005, BUG-001-orig, BUG-002).
   - Track 2 (`kredit_lab_classify_track2.py`) is on `track-2-development`.
     Today's BUG-002 fix was committed there first (`51c2a1d`) then
     cherry-picked to `main` (`f9d1377`).

3. **Deploy flow for Track 1 bug fixes:**
   Edit on `track-2-development` → cherry-pick to `main` → push `main`.
   Railway reads `main`. Don't merge whole branches; Track 2 commits are
   not production-ready.

4. **Spec patch is uncommitted at session close.** Located at
   `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md`,
   working-tree modification on `track-2-development`. This handoff doc
   itself is also untracked. Commit both when ready.

---

## Files modified across both sessions

Session 1 (2026-05-11):
- `app.py` ~1438-1500 — recognise OPENING BALANCE alongside BEGINNING BALANCE (commit `b023d7b`)
- `app.py` ~601-617 — drop `_prev_month` rollback in `extract_cimb_statement_totals` (commit `d558e4e`)
- `app.py` ~1239-1264 — dominant-txn-month override in CIMB `monthly_summary` branch (commit `d558e4e`)

Session 2 (2026-05-12):
- `app.py:4297` — `\b` after Malaysia-marker alternation in `_normalise_counterparty` (commit `f9d1377`)
- `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md` — five-point verification gate (working tree, uncommitted)

No bank parser modules (`maybank.py`, `cimb.py`, etc.) were modified across either session. All Track 1 fixes land in `app.py`'s monthly-summary, CIMB-extractor, and counterparty-normalisation logic.

---

## Suggested next-chat opening

> Track 1 maintenance complete for HUAHUB. Three real parser bugs shipped
> (`b023d7b`, `d558e4e`, `f9d1377` on `origin/main`). Spec patch with
> five-point verification gate applied to `SYSTEM_PROMPT_v3_5_6.md`
> (uncommitted at session close). One real `missing_bank_patterns[]`
> entry deferred: HLB counterparty extraction (LIM-001). Ready to pivot
> to Track 2 / V3-B Auto-RP / next entity at your call.
