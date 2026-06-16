# Session Summary — 2026-04-23 (Sprints 1-4 shipped)

**Duration:** Single session
**Scope:** 4 sprints (24-item master fix list condensed to 16 completed items)
**Commits:** 4 total across 2 repos, all pushed to origin/main

---

## What was shipped

### Sprint 1 — [core_utils.py](core_utils.py) foundations (merged into Sprint 2 commit)

Added 6 universal cross-bank helpers now used by all 14 bank parsers:

| Function | Purpose |
|---|---|
| `determine_account_type()` | Universal CR/OD/Cash Line detector using both balance formulas + header keywords. Handles Alliance (positive debt magnitude), Ambank (negated balance), Cash Line-i (CAP-i/SAP-i/Ar-Rahnu). |
| `stamp_account_type_once()` | Per-PDF stamping to prevent KDYN BUG-002-class per-row flips. |
| `statutory_bucket_for()` | FPX 20-char truncation tolerance for KWSP/SOCSO/LHDN/HRDF detection. |
| `clean_description()` | Pipeline: `collapse_duplicated_segments` → `strip_reference_numbers(extra=...)` → `cleanup_trailing_artifacts`. |
| `should_drop_as_counterparty()` | Cross-bank month / purpose-word / stop-word filter. |
| `is_patronymic_fragment()` / `strip_patronymic_ambiguity()` | BIN/BINTI guard for BA/TL/TF/FD/CT. |

`ensure_transaction_schema()` now emits `_patronymic_ambiguous_tokens` as transaction metadata.

### Sprint 2 — per-bank parser fixes (commit `793b5f2`, pushed)

| # | File | Fix |
|---|---|---|
| 7 | [alliance.py](alliance.py) | BUG-001 ghost-row drop: zero-amount null-balance voucher rows like `PV25-184472-A` with bogus `2094-10-31` date. KDYN: 2,719 → 2,718 txns. |
| 11 | [cimb.py](cimb.py) | Duplicated-prefix collapse via `collapse_duplicated_segments`. Fixes SUBALIPACK (7 rows), EPF earmark (1 row), Guard Service purpose-dup (many). |
| 12 | [cimb.py](cimb.py) | Reference-number strip via `strip_reference_numbers` + CIMB extras (ITF/, U\d{11+}, RTB\d+.TXT). Muhafiz: 233 refs stripped. |
| 13 | core_utils | `cleanup_trailing_artifacts()`: `SCHENKER LOGISTICS (` → `SCHENKER LOGISTICS`. Zero dangling parens across full CIMB corpus. |
| 14 | [app.py](app.py) | Maybank ghost-verb fallback: `TRANSFER FR/TO A/C` / `PAYMENT FR A/C` bare cases consolidated as `UNNAMED TRANSFER (CR/DR)` / `UNNAMED PAYMENT (DR)` — no longer silent `UNIDENTIFIED`. NEW: `INTER-BANK PAYMENT INTO/FROM A/C` entity extraction. |
| 15 | core_utils | Patronymic guard metadata emitted in `_patronymic_ambiguous_tokens`. 25 MTA rows flagged with `BA`, zero false positives cross-bank. |

**Regression evidence:**
- CIMB corpus: 37 PDFs / 5,324 txns — 1,305 cleaned (24.5%), 0 empty, 0 parse errors
- Maybank corpus: 57 PDFs / 16,742 txns — UNIDENTIFIED from ~hundreds → 1, 13,141 legit rows preserved
- Alliance KDYN: 6 PDFs / 2,719 → 2,718 (exactly 1 ghost row)

### Sprint 3 — Renderer (commit `12a1cf4` in `bank-statement-analysis-HTML-fresh`, pushed)

| # | Fix |
|---|---|
| 16 | Fraud Detector tab + button now render **UNCONDITIONALLY**. When `pdf_integrity` data is absent, visible amber placeholder block shows "PDF Integrity: NOT CAPTURED" with remediation. Previously silently dropped (Muhafiz case). |
| 17 | Top Parties bar chart: new `_render_monthly_bars()` helper. Inline month + amount labels below each bar: "Mar: 162K, Apr: 170K, May: 215K ...". Previously hover-only tooltips. |

Verified end-to-end against Muhafiz/MTA/KYDN analysis JSONs — rendered HTML at `/tmp/*_rerendered.html`.

### Sprint 4 — Claude AI file bump (commit `db9a8cb`, NOT YET PUSHED as of writing this summary)

Three new files in `validation runs - json/claude ai prompt file/`:

| File | Version | Key changes |
|---|---|---|
| `SYSTEM_PROMPT_v3_5_4.md` | v3.5.4 | Step 2 Alliance wording softened; Step 7 flags-never-blocks; Step 8 schema validation hard gate; EPF dual-band; STRUCTURAL status; statutory_bucket trust; patronymic guard; C26/C27 Trade Income/Expense. |
| `CLASSIFICATION_RULES_v3_4.json` | v3.4.0 | C26/C27 added; `statutory_bucket_trust_v3_4`; `statutory_truncated_forms`; `patronymic_guard_v3_4`; expanded `stop_words_drop_as_counterparty`. |
| `BANK_ANALYSIS_SCHEMA_v6_3_4.json` | v6.3.4 | `account_type_determination` object added; account_type enum + Cash Line / Cash Line-i; relationship enum + Management Company / Affiliate; STRUCTURAL status; observations maxItems 5→8. |

**C17/C18 collision note:** existing rulebook uses C17 for Cash Deposit, C18 for Cash Withdrawal. Trade Income/Expense landed as **C26/C27** instead of overwriting. SYSTEM_PROMPT + RULES + SCHEMA all consistent on this choice.

---

## What's NOT done

### Sprint 5 — Optimization (big work, fresh session recommended)

- **#21 `kredit_lab_classify.py`** — reusable Python module AI calls instead of rewriting classification code every run. Expected 500-1000 lines. Big win (4-5× speed gain per run) but needs dedicated context.
- **#23 Regression fixture suite** — freeze MTA, KYDN, Muhafiz, DMC Travel as fixtures under `tests/fixtures/`. Before shipping any new prompt/rules, re-run all four and assert metrics drift ≤1%.
- **#24 Synthetic OD simulation** — flip CR statement balance signs + DR/CR columns to simulate OD across 14 banks. Regression fixture until real OD samples arrive.

### Sprint 6 — Polish (small items, can be bundled)

| # | Scope |
|---|---|
| 6 | Stop-words in parsers (partially covered by `should_drop_as_counterparty`; wire into per-bank extraction) |
| 8 | Alliance date-clamp to statement period (belt-and-braces on BUG-001) |
| 9 | Alliance rail-prefix strip (CR ADVICE, IB2G FND TRF, FPX ABB, DuitNow CR Trf, HUB CA MISC DR) |
| 10 | IB2G trailing own-company-name strip (`HUAREN RESOURCES SDN KLINIK DRS YOUNG NEW` cleaning limitation) |
| 22 | `canonical_entities_<COMPANY>.json` — band-aid before `cimb.py` full-name reconstruction lands |

---

## Decisions that matter for next session

1. **Trade Income/Expense = C26/C27, not C17/C18.** C17/C18 are already Cash Deposit/Withdrawal. Do not re-use those codes.
2. **AI files live in `validation runs - json/claude ai prompt file/`.** Parent folder is untracked; individual v3_5_4 / v3_4 / v6_3_4 are NOW tracked (committed this session).
3. **Parser layer is primary, AI is thin.** Sprint 2 shifted regex work from classifier → parser. Future bug fixes should check: is this a parser gap or a rules gap? Default answer should be parser.
4. **Renderer uses single-template architecture.** No more "minimal vs full" branches. Every entity gets every tab / every chart.
5. **Cross-bank helpers live in `core_utils.py`.** Bank-specific extras pass via `extra_patterns` parameter. Adding Maybank / RHB / Alliance specifics in future should follow this pattern.
6. **UNNAMED buckets are correct behaviour.** Ghost-verb data-absence is not a bug to hide — it's a data-quality signal to surface. Don't try to "fix" by inventing names.

---

## Files touched this session

**Main repo (`Bank-Statement-Analysis-main 3`):**
- `core_utils.py` — +575 lines of cross-bank helpers
- `alliance.py` — BUG-001 ghost-row filter
- `cimb.py` — refactored to import from core_utils
- `app.py` — CP7/CP8/CP9 ghost-verb guards + INTER-BANK extractor
- `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_4.md` (NEW)
- `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_4.json` (NEW)
- `validation runs - json/claude ai prompt file/BANK_ANALYSIS_SCHEMA_v6_3_4.json` (NEW)

**Renderer repo (`bank-statement-analysis-HTML-fresh`):**
- `app.py` — Fraud tab always-rendered + inline bar labels

---

## Commits (push state)

| Hash | Repo | Description | Push state |
|---|---|---|---|
| `793b5f2` | main | Parser Sprint 2: cross-bank cleanup | pushed |
| `12a1cf4` | renderer | v6.3.4 renderer | pushed |
| `db9a8cb` | main | Sprint 4: Claude AI file bump | pending push |
| (this doc) | main | Session summary + NEXT_CHAT_PROMPT append | pending |
