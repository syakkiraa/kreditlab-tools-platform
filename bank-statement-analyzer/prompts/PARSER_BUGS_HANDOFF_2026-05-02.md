# Parser Bugs Handoff — 2026-05-02 (post Kay R re-grade)

Hand this to a new chat session as the opening prompt.

---

## Context — what just happened

Yesterday (2026-05-01) we **re-parsed RHB Kay R** through the Streamlit app on `sprint-6/polish` and re-graded it through claude.ai. The grade went **D → C**, not D → A as predicted. The re-parse DID fix the headline issue (raw_fallback 100% → 0.4%, pattern_matched 0 → 166), but it exposed 5 deeper parser bugs that were always there, just hidden behind the counterparty-extraction noise.

Files just produced (saved to disk):
- [validation runs - json/AI Analyzed Json/KAY R RESOURCES (M) SDN BHD/KAY_R_RESOURCES_analysis.json] — the full v6.3.5 analysis
- [validation runs - json/AI Analyzed Json/KAY R RESOURCES (M) SDN BHD/KAY_R_RESOURCES_parser_quality_report.json] — the parser quality grade C report

(If those paths don't exist on disk yet, the user has them in chat context.)

## Repo state

| Ref | SHA | Status |
|---|---|---|
| Local `HEAD` (sprint-6/polish) | `39fa68a` | Synced with origin |
| `origin/sprint-6/polish` | `39fa68a` | All 31 commits pushed yesterday |
| `origin/main` (Railway production) | `a4b2bca` | Sprint 4.5 — has NONE of the recent fixes |

Today's two commits already in the 31 pushed:
- `6afb133` — `core_utils.py` SOCSO regex extension (KESELAMA + bare PERTUBUH CP)
- `29de7ed` — `CLASSIFICATION_RULES_v3_5.json` v3.5.1 → v3.5.2 alignment

Kay R's parser quality report does NOT mention SOCSO bugs, confirming today's commits work as intended (Kay R has 0 SOCSO transactions).

## Architecture (3 layers — keep them isolated)

- **Parser** (shared upstream): `app.py`, `core_utils.py`, all `*.py` bank parsers. Runs locally + on Railway. THIS IS WHERE THE 5 BUGS LIVE.
- **Track 1** (claude.ai): `SYSTEM_PROMPT_v3_5_6.md`, `CLASSIFICATION_RULES_v3_5.json` v3.5.2, `BANK_ANALYSIS_SCHEMA_v6_3_5.json`. Manual upload to claude.ai by user.
- **Track 2** (local CLI): `kredit_lab_classify.py`. Runs only on user's laptop. Hard rule: never edit from Track 1 work.

The 5 Kay R bugs are PARSER bugs. Fixing them does NOT require Track 1 prompt changes (assuming we don't change the JSON schema shape). It does NOT require Track 2 changes.

---

## The 5 open bugs from Kay R quality report

### BUG-001 (HIGH) — monthly_summary footer double-counting

**Symptom:** For all 6 months, `monthly_summary[*].total_debit` and `total_credit` are inflated relative to the sum of individual transactions, by an **identical amount on both sides each month**:

| Month | DR/CR inflation |
|---|---|
| 2025-08 | +RM 177,122.42 |
| 2025-09 | +RM 523,001.26 |
| 2025-10 | +RM 156,867.72 |
| 2025-11 | +RM 665,882.28 |
| 2025-12 | +RM 365,460.11 |
| 2026-01 | +RM 228,361.00 |

The fact that inflation is mirrored on DR and CR sides strongly suggests the parser is treating a balanced row (like a statement footer "Total Debits / Total Credits" line, or a brought-forward / carried-forward row) as both a debit AND a credit entry.

The transactions array itself is correct (sums match individual rows). The bug is in `monthly_summary` aggregation only.

**Fix approach:**
- Re-derive `monthly_summary` totals by summing the `transactions` array directly, instead of separately parsing footer.
- OR add a guard that skips lines containing `TOTAL DEBIT` / `JUMLAH DEBIT` / `STATEMENT TOTAL` headers.

**Probable file:** `app.py` `_build_monthly_summary` or similar. Could also be in `rhb.py` if RHB-specific.

**Investigation start:** grep `app.py` and `rhb.py` for `monthly_summary` and `total_debit` to find the aggregation function.

---

### BUG-002 (HIGH) — Specific row at 2025-08-15 has wrong amount-to-description binding

**Symptom:** The row `RFLX INSTANT TRF SC DR 0000003847 CM112` on 2025-08-15 has amount **RM 138,791.36**. Every other RFLX SC row in the entire dataset has amount RM 0.50 (the standard service charge). Balance trail confirms RM 138,791.36 is a real outflow — but the description and amount are mismatched.

The reference number `0000003847` matches the next row's `RFLX INSTANT TRF DR 200,000`, which means the same transfer instruction was split across what should have been 3 PDF rows (fee, transfer, beneficiary) but came out as 2 rows with incorrect amount-to-description binding on the first.

**Fix approach:**
- Sanity check: when description matches `^RFLX\s+INSTANT\s+TRF\s+SC` and amount > RM 1.00, log as parser warning and route to a "needs review" bucket.
- Investigate the specific PDF page (RHB AUG 2025.pdf, around 2025-08-15) to understand the multi-line layout.

**Probable file:** `app.py` (the RFLX handler near line 3197+) or `rhb.py` (the layout-based extractor).

---

### BUG-003 (MEDIUM) — Company suffix truncation `SDN BHD` → `SDN B`/`SB`/`SDN BH`

**Symptom:** 25 entries have suffixes cut mid-token by PDF column-width clipping:
- `WILMAR AGRIFERT PULAU INDAH SB` (should be `SDN BHD`)
- `SCANIA CREDIT (MALAYSIA) SDN B`
- `KAY R WORKSHOP (M) SDN. B`
- `DANAZ DIMENSI SDN BH`
- `AGRO SURGE FERTILIZER SDN`

**Fix approach:** Add a suffix normalizer:

```python
import re
SUFFIX_NORM = re.compile(r'\b(SB|SDN\s*\.?\s*B|SDN\s*\.?\s*BH|SDN\s*\.?\s*BHD\.?)\s*$', re.I)
def normalize_suffix(name: str) -> str:
    return SUFFIX_NORM.sub('SDN BHD', name).strip()
```

Apply during counterparty extraction in `app.py` `_extract_counterparty` AND/OR in `core_utils.py` cleanup functions.

**Cross-bank consideration:** This affects every bank, not just RHB. The fix belongs in `core_utils.py` so all parsers benefit.

---

### BUG-004 (MEDIUM) — Own-party detection — KAY R RESOURCES in 3 different buckets

**Symptom:** All 3 own-party CR transactions name `KAY R RESOURCES`, but parser bucketed them as:
1. `KAY R RESOURCES (OWN-PARTY)` — RM 50K (correctly attributed) ✓
2. `UNNAMED RHB TRANSFER (CR)` — RM 4,452 from "INWARD IBG 0000003168 KAY R RESOURCES SETTLEMENT" ✗
3. `RESOURCES` — RM 120,000 from "KAY R RESOURCES (M) SDN. BHD. KAY R RESOURCES PINDAHAN" ✗

Detector requires the exact full company name + a `PINDAHAN DANA` marker. Partial matches drop into different buckets.

**Fix approach:**

```python
def is_own_party(candidate: str, company_name: str) -> bool:
    cand_norm = normalize(candidate)
    comp_norm = normalize(company_name)
    if not cand_norm or not comp_norm:
        return False
    if cand_norm in comp_norm or comp_norm in cand_norm:
        return True
    cand_tokens = set(cand_norm.split())
    comp_tokens = set(comp_norm.split())
    overlap = cand_tokens & comp_tokens
    return len(overlap) >= 2 and len(overlap) / len(comp_tokens) >= 0.5
```

**Probable file:** `app.py` `_extract_counterparty` own-party check, or wherever `(OWN-PARTY)` suffix gets stamped.

---

### BUG-005 (LOW) — 2 ghost-verb-only descriptions (multi-line PDF rows not merged)

**Symptom:** Two CR transactions have descriptions stripped to reference-number-only:
- `INWARD IBG 0000087207 Interbank GIRO 23350PWINT9` RM 196,675.76 (2025-08-27)
- `INWARD IBG 0000082306 47` RM 18,629.50 (2026-01-23)

The originator name landed on a separate PDF line that the parser didn't merge in. Combined RM 215K is unclassifiable.

**Fix approach:** Improve PDF row-merging in `rhb.py`. When a description ends with a reference-number-only suffix and the next PDF line on the same date contains a name-shaped token (≥ 2 capitalized words OR `BIN/BINTI` + name), merge.

**Effort:** Need to look at the specific PDF pages to confirm the layout assumption.

---

## Suggested order

1. **BUG-001 first** (2 hours estimated) — fastest, highest impact. Code-only fix, doesn't need PDF inspection. Removes a lurking data-quality issue that affects every parsed report.
2. **BUG-003 next** (1 hour) — additive normalizer in `core_utils.py`, benefits all 14 banks. Test against existing reports.
3. **BUG-004 next** (1-2 hours) — own-party detector improvement. Test by re-parsing JATI WAJA + Kay R + 1 more company.
4. **BUG-002** (2-3 hours) — needs PDF inspection. Investigate the 2025-08-15 page in RHB AUG 2025.pdf.
5. **BUG-005** (2-3 hours) — PDF row-merging. Lowest priority because it only affects 2 rows.

**After each fix:**
- Run `python3 scripts/validate_reference_statements.py` (14-bank validator) — must pass.
- Re-parse Kay R headlessly to confirm the bug is gone.
- Don't commit until validator passes.

## Hard rules carried over

1. Never edit `kredit_lab_classify.py` from this work (Track 2 isolation).
2. Never edit `prompts/NEXT_CHAT_PROMPT.md` (Track 2's handoff channel).
3. Never push to remote without explicit user OK. (Currently 0 ahead of origin/sprint-6/polish.)
4. 14-bank validator must PASS after every parser change.
5. No `--no-verify`, no force push, no `--amend` of pushed commits.

## What NOT to do

- Don't merge `sprint-6/polish` → `main` until BUG-001 (the data-quality one) is fixed. Every Full Report users generate today has inflated `monthly_summary` totals — shipping that to production amplifies the bug.
- Don't re-grade other companies on claude.ai yet. Kay R's grade C tells us re-grading more companies will surface the same 5 bugs across all of them. Better to fix the bugs first, THEN batch re-grade everyone.
- Don't get distracted by suffix-truncation edge cases that aren't `SDN BHD` (e.g. `BERHAD`, `LIMITED`, `LTD`). The cleanest fix is a normalizer that handles common Malaysian suffixes.

## What ChatGPT/Claude in the new session needs to know about today's prior work

Already done (don't redo):
- ✅ JATI WAJA re-graded D → A (validated stale-data hypothesis)
- ✅ SOCSO regex extended for KESELAMA + bare PERTUBUH CP truncations (`6afb133`)
- ✅ Classification Rules v3.5.2 aligned with parser regex (`29de7ed`)
- ✅ All 31 local commits pushed to `origin/sprint-6/polish` yesterday
- ✅ Audit done: 26 of 28 sample-corpus Full Reports are stale; 2 fresh
- ✅ Kay R re-parsed headlessly: pattern_matched 0 → 166 (72.5%), raw_fallback 229 → 1, counterparties 228 → 44
- ✅ Kay R re-graded by claude.ai: D → C, with 5 new bugs flagged

NOT yet done:
- ⏳ The 5 bugs above (this is the new session's job)
- ⏳ Re-grade other high-impact companies (Bank Rakyat Felcra, BIMB Mytutor, PBB Mazaa) — DO THIS AFTER bug fixes ship
- ⏳ Merge `sprint-6/polish` → `main` to deploy to Railway — DO THIS AFTER bug fixes + multi-company validation

---

## Single starting question for the new chat session

"Read [prompts/PARSER_BUGS_HANDOFF_2026-05-02.md](../prompts/PARSER_BUGS_HANDOFF_2026-05-02.md) and start with BUG-001 (monthly_summary footer double-counting). Find the aggregation code in `app.py` or `rhb.py`, propose a fix, run the 14-bank validator, then re-parse Kay R headlessly to confirm the inflation is gone."
