# Classifier Build Handoff — `kredit_lab_classify.py`

Self-contained brief for a fresh Claude Code session to build the new local classifier. Open this file as the first read in the new session. Everything you need is referenced from here.

---

## Goal

Build a new Streamlit application **`kredit_lab_classify.py`** at the project root. This module replaces the AI-heavy `claude.ai` web workflow for bank statement classification with a **mostly-deterministic local Python pipeline**, calling AI only for narrative observations on a small focused brief.

---

## The 4-stage pipeline this fits into

```
PDF
  ↓ (Stage 1: app.py — already exists, do NOT touch)
full_report.json
  ↓ (Stage 2: kredit_lab_classify.py — THIS BUILD)
analysis.json (95% complete) + narrative_brief.json (~10 KB)
  ↓ (Stage 3: claude.ai web — narrative only, manual paste-back)
narrative observations merged into analysis.json
  ↓ (Stage 4: bank-statement-analysis-HTML-fresh/ — already exists)
HTML report
```

You're building **only Stage 2**. Stages 1, 3, 4 already exist or are external.

---

## Why we're building this

The 2026-04-22 efficiency review ([validation runs - json/22 april 2026 - result HTML(MTA,KYDN,MSSB)/Test Bank Staement/MTA/KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md](../validation%20runs%20-%20json/22%20april%202026%20-%20result%20HTML%28MTA%2CKYDN%2CMSSB%29/Test%20Bank%20Staement/MTA/KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md)) diagnosed: AI is currently doing 9,000-row classification + narrative + math + schema-shaping in one giant prompt, which hits 20-45 minutes per file with 3 reruns typical. This module moves the deterministic 80% (rules-based classification, math, structure) into local Python, leaving only the 20% that needs judgment (narrative observations, ambiguous RP4 candidates) for the AI.

**Read that doc first** — section 2.1 names this exact module and proposes its structure. Section 4 has the function skeleton to follow. Don't re-derive what's already specified there.

---

## User preferences (load-bearing, don't violate)

- **UI required.** No pure-CLI scripts. Use Streamlit (matches existing `app.py` and `fraud_app.py` UX).
- **No Anthropic API key.** Don't introduce `pip install anthropic`. The user prefers claude.ai web for the AI portion (narrative_brief.json gets pasted manually). API integration can come later — first version must run without it.
- **Cross-bank only** for any classification logic — no bank-specific hacks. The classification rules in `CLASSIFICATION_RULES_v3_5.json` are already cross-bank-safe.
- **Trust parser metadata.** When `full_report.json` carries `statutory_bucket`, `account_type_determination`, `_patronymic_ambiguous_tokens`, etc., trust them. Do not re-regex the description. (This is the v3.5.4 thesis — see `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_5.md` for the rationale.)

---

## Source files to read before writing code

In order, these are the files to load into context:

1. **[KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md](../validation%20runs%20-%20json/22%20april%202026%20-%20result%20HTML%28MTA%2CKYDN%2CMSSB%29/Test%20Bank%20Staement/MTA/KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md)** — section 2.1 (this exact module) and section 4 (function skeleton). The architecture is already designed; you're implementing it.
2. **[CLASSIFICATION_RULES_v3_5.json](../validation%20runs%20-%20json/claude%20ai%20prompt%20file/CLASSIFICATION_RULES_v3_5.json)** — the rule dictionary. Every classifier function maps a rule from this file to Python.
3. **[BANK_ANALYSIS_SCHEMA_v6_3_5.json](../validation%20runs%20-%20json/claude%20ai%20prompt%20file/BANK_ANALYSIS_SCHEMA_v6_3_5.json)** — the output structure. Use `jsonschema.validate()` as a hard gate before write.
4. **[SYSTEM_PROMPT_v3_5_6.md](../validation%20runs%20-%20json/claude%20ai%20prompt%20file/SYSTEM_PROMPT_v3_5_6.md)** *(or v3.5.5 if 5.6 not yet shipped)* — for context on what the AI used to do. Don't reimplement the *defensive re-extraction* parts; those got cut in 5.6 because Layer 1 (parser) handles them now.
5. **[app.py](../app.py)** — already-shipped parser. Read `_extract_counterparty()` and the bank-specific helpers — they're the source of truth for counterparty extraction. **Do NOT modify `app.py`** under any circumstance. Just reference its logic.
6. **[core_utils.py](../core_utils.py)** — shared helpers (`normalize_transactions`, `dedupe_transactions`, `transaction_fingerprint`, the canonical schema). Reuse these. Extending is OK if needed.
7. **A real `full_report.json`** — pick `validation runs - json/claude ai prompt file/Full Report Sample/Full Report CIMB Muhafiz.json` (~408K tokens, mid-size, fits in 1M context). Read the input shape before writing the consumer.
8. **A real `*.classified.json`** — `Full Report Alliiance KYDN.classified.json` or similar. Read the output shape that the AI was producing — yours must be schema-equivalent.

---

## Module structure (from `KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md` §4)

```
kredit_lab_classify.py
├── load_parser_output(path)             → dict
├── detect_account_type(data)            → {type, convention, is_od}
├── reconcile_balance_trail(data, conv)  → {pass, deltas}
├── scan_related_party_candidates(data)  → [{name, method, confidence, evidence}]
├── scan_purpose_clusters(data)          → {clusters, dominant, needs_confirmation}
├── classify_transactions(data, rulebook, analyst_decisions)
│                                        → classified[]
├── build_monthly_analysis(classified)   → [monthly]
├── build_consolidated(monthly)          → dict
├── build_top_parties(classified)        → dict
├── build_flags(consolidated, monthly)   → [flags]   # exactly 16
├── build_narrative_brief(consolidated, flags, related_parties, patterns)
│                                        → dict (for claude.ai web)
├── assemble_analysis_json(...)          → dict (validates against schema v6_3_5)
├── build_parser_quality_report(...)     → dict (Deliverable 2)
└── streamlit_main()                     → Streamlit UI entrypoint
```

The Streamlit UI binds these together — the user sees a drag-drop, a "Classify" button, decision prompts for ambiguous rows, and download buttons for the outputs.

---

## What ships in V1 (first version)

**In scope:**
- Streamlit UI with: drag-drop `full_report.json`, related-parties text-area input, factoring-entities text-area input, "Classify" button, status panel, download buttons for `analysis.json` + `narrative_brief.json` + `parser_quality.json`.
- Deterministic classification for all categories that don't require interpretive judgment:
  - **C01/C02** own-party
  - **C05** salary (CIMB AUTOPAY DR + keyword list)
  - **C06–C09** statutory (trust `statutory_bucket` from parser; fallback to keyword)
  - **C10** factoring (only when `F ADVANCE` keyword + known factoring entity from input list)
  - **C11** loan repayment (own-party + loan keyword; account-number-only loans per v3.5.3 rule)
  - **C12** FD/interest
  - **C13** reversals
  - **C14–C20** cheques + cash
  - **C21–C23** monitoring flags
  - **C24** bank fees
  - **C25** balance-row filter (must run FIRST per classification order)
  - **C26/C27** trade income / trade expense (counterparty-pattern-based)
- `monthly_analysis[]` aggregation (per-month rollups, all 48+ schema fields).
- `consolidated` aggregation including `statutory_compliance` sub-object (EPF/SOCSO coverage via set intersection, per v3.5.3 rule; LHDN/HRDF as informational only).
- `top_parties.top_payers[]` and `.top_payees[]` with ghost-verb suppression.
- `flags.indicators[]` — exactly 16 entries, fixed order, with templated remarks pulled from data.
- `narrative_brief.json` writer — small structured brief (~5-10 KB) summarising headline numbers, detected patterns, missing months, RP4 candidates, asks for narrative.
- `parser_quality.json` writer (Deliverable 2 — grade A-F based on `effective_match_rate`, balance-trail status, description quality counts).
- Schema validation hard gate (`jsonschema.validate(...)`) before write.

**Out of scope for V1:**
- C03/C04 related-party classification — needs analyst decisions; first version surfaces candidates in UI for analyst confirmation, then re-classifies. Don't auto-decide RP4 beyond HIGH-confidence (RP2 root-name, RP7 SHARE CAPITAL).
- Counterparty ledger M1-M7 merging — defer to V2; first version emits the parser's `counterparty_ledger` unchanged plus M7 canonical-RP-name stamping.
- Anthropic SDK integration for narrative — V1 outputs `narrative_brief.json` for **manual** claude.ai web upload; SDK can come later.
- Affin (OCR-only bank) — leave classification rows as Unidentified, don't try to extract from OCR garbage.

---

## Test plan for V1

After build, run on these representative files (all in `validation runs - json/claude ai prompt file/Full Report Sample/`):

| File | Tokens | Why |
|---|---:|---|
| Full Report CIMB Muhafiz.json | ~408K | Mid-size, real corpus, has known RP4 candidates (per MYTUTOR doc parallels) |
| Full Report Alliiance KYDN.json | ~1M | Larger, OD account exercise |
| Full Report OCBC Calvin Skin.json | ~430K | OCBC bank coverage check |
| Full Report Maybank Hydrise Jul25-Dec25.json | ~313K | Smaller smoke test |

For each: produce `analysis.json` + `narrative_brief.json` + `parser_quality.json`, schema-validate, eyeball the numbers against the corresponding existing `*.classified.json` (the AI-produced reference). Numerical fields should match within rounding (±RM1.00 on totals); structural fields exact.

Don't worry about narrative content matching — the brief gets that done in claude.ai web.

---

## Hard rules (don't violate)

1. **Don't modify `app.py`, `fraud_app.py`, `core_utils.py` except to add new helpers** — the parser is production. Cross-imports only.
2. **Don't modify any parser module (`maybank.py`, `cimb.py`, etc.)** — they're tested.
3. **Don't add an Anthropic API key requirement** — V1 must run with `pip install -r requirements.txt` + `streamlit run kredit_lab_classify.py`. No new env vars beyond what the project already needs.
4. **Don't change `CLASSIFICATION_RULES_v3_5.json` or `BANK_ANALYSIS_SCHEMA_v6_3_5.json`** — these are the source of truth; classifier consumes them, doesn't mutate them.
5. **Schema-validate before write** — `jsonschema.validate(analysis, schema)` is a hard gate per v3.5.4 Step 8. If validation fails, don't write the output file; surface error in UI.
6. **Trust parser metadata** — `statutory_bucket`, `account_type_determination`, `_patronymic_ambiguous_tokens` are authoritative when present.

---

## Coordination with the parallel slim-down track

A separate session is shipping `SYSTEM_PROMPT_v3_5_6.md` (cuts defensive extraction logic from the AI prompt). That work is independent of this build:

- The slim-down doesn't change classification rules or schema → no impact on this module.
- The classifier's `narrative_brief.json` output is consumed by the AI prompt — but the brief format is up to *this* track to design. Just reference v3.5.6 as the target prompt version when designing the brief schema.
- Both tracks commit to separate files; no merge conflicts.

If the slim-down ships first, link to v3.5.6 in the narrative_brief metadata (`"target_prompt_version": "v3.5.6"`). If not yet shipped, reference v3.5.5 — the brief format doesn't change either way.

---

## First actions in the new session

1. Read this file.
2. Read [KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md](../validation%20runs%20-%20json/22%20april%202026%20-%20result%20HTML%28MTA%2CKYDN%2CMSSB%29/Test%20Bank%20Staement/MTA/KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md) sections 2.1 and 4.
3. Read `CLASSIFICATION_RULES_v3_5.json` and the schema `BANK_ANALYSIS_SCHEMA_v6_3_5.json`.
4. Read one full_report sample (CIMB Muhafiz) and one corresponding `*.classified.json` — understand input and target output shapes.
5. Read `core_utils.py` and the relevant `_extract_counterparty*` helpers in `app.py` — these are the prior-art for the deterministic classification logic.
6. Sketch the module skeleton (function stubs only, schema-aligned), share with user for approval.
7. Implement `streamlit_main()` + the simplest end-to-end happy path: load JSON → classify C01 + C24 only → produce minimal valid analysis.json. Ship that first as the smallest-possible end-to-end demo.
8. Add categories one at a time, schema-validating after each.

---

## Why this approach

The MYTUTOR doc estimates this module gets you **~4-5× speed gain** on classification runs by eliminating the rerun loop. The biggest single win is having the classification logic **executable, deterministic, and version-controlled** — not re-derived in Claude's head from prose every run.

V1 ships the deterministic core. V2 adds related-party intelligence + ledger merging. V3 wires up the SDK for fully-automated narrative. Each version is independently useful.
