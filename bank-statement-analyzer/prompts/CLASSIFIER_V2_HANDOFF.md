# Classifier Build Handoff — V2 (Track 2 completion)

Self-contained brief for a fresh Claude Code session to finish `kredit_lab_classify.py`. Open this file as the first read in the new session.

---

## Where we are

**V1.1 shipped** on branch `sprint-6/polish`, commit `d900f03` (V1 was `bfda34c`).

- Streamlit module at repo root: `kredit_lab_classify.py` (~1500 lines, 43+ functions)
- 29/29 corpus files schema-validate against `BANK_ANALYSIS_SCHEMA_v6_3_5`
- 99% rulebook-consistent on CIMB Muhafiz vs the (older) AI reference
- Generates 3 deliverables: `analysis.json` (hard-gated by `jsonschema.validate`), `narrative_brief.json`, `parser_quality.json`
- Categories already wired: C01/C02 (own-party), C03/C04 (analyst-textarea-driven), C05 (incl. STAFF OVERTIME / STAFF INCENTIVE / STAFF BONUS / STAFF ADVANCE), C06–C09 (statutory), C10 (factoring with analyst entity list), C11 (loan repayment), C12 (FD/interest), C13 (reversal), C14/C15 (returned cheques — keyword fallback only, untested), C16 (IBG inward return), C17/C18 (cash dep/wdl), C19/C20 (cheque dep/issue), C24 (bank fees), C25 (balance rows)

Run `streamlit run kredit_lab_classify.py` — it works end-to-end.

---

## Goal of this session

Finish Track 2 by closing the **V2 scope** below. V3 (Anthropic SDK narrative automation + end-to-end PDF→HTML pipeline glue) is a separate follow-up session.

---

## V2 scope (this session)

### V2.1 — C26/C27 trade rules **[biggest impact]**

Today most non-payroll files have 75%+ rows unclassified — that residual flow IS real trade (customer payments inbound, supplier payments outbound). Adding C26 (trade income, CR) + C27 (trade expense, DR) catches it.

**Approach**: default rule. Any row that survives all V1.1 checks AND has a named counterparty (not in `BUCKET_TO_CATEGORY`, not own-party, not related-party, not analyst-flagged factoring) gets:
- `C26` if side == CR
- `C27` if side == DR

Schema fields already exist: `trade_income_count`, `trade_income_amount`, `trade_expense_count`, `trade_expense_amount`. Wire into `build_monthly_analysis` + `build_consolidated`.

**Audit BEFORE coding**: sample 10–15 random `Full Report Sample/*.json` files, look at the top 20 unclassified counterparties per file, confirm they look like real customers/suppliers (entity names, not garbage). If yes, default rule is safe. If no, fall back to keyword-based variant (`INV`, `INVOICE`, `PURCHASE`, `ORDER`, `BILL`, etc.).

**Expected uplift**: Muhafiz 49% → 80%+; corpus average ~10% → 65%+.

### V2.2 — RP4 auto-apply confirmation flow

V1.1's `scan_related_party_candidates()` already surfaces RP4 candidates (3 on Muhafiz: SHAHARUDDIN BIN SAMS, DAYANG SITI RAUDZAH, SAMSI BIN IBRAHIM). They're info-only in `narrative_brief.json`.

**V2 change**: render candidates as a checkbox list in the Streamlit UI between gate and classify. When the analyst confirms one, it's appended to `decisions.related_parties` and the classifier re-runs (closes loop on C03/C04 firing).

This requires a **two-pass UI** (gate → confirm → classify), replacing the current single-button flow. Use `st.session_state` to persist gate output across reruns.

### V2.3 — M1–M7 counterparty merging

Variants like `PLANWORTH GLOBAL` + `PLANWORTH GLOBAL S` + `PLANWORTH` should canonicalize to one entity. Today `top_parties` shows them as separate rows.

**Look first** at `validation runs - json/quality report parser/` (untracked dir per git-status) — it may contain prior M1–M7 specification. If absent, implement based on:
- **M1**: strip suffixes — SDN BHD / BERHAD / ENTERPRISE / HOLDINGS / TRADING / SERVICES / PLT (use existing `_company_root` helper from V1.1)
- **M2**: strip parenthetical disambiguators `(M)`, `(SARAWAK)`, etc.
- **M3**: token-set substring match — short variant is contained in long one
- **M4**: fuzzy match on normalized core (Levenshtein ≤ 2 for tokens ≥ 5 chars)
- **M5–M7**: TBD; check architecture doc `KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md` for any spec

Apply merging in `build_top_parties` and pass-through to `counterparty_ledger`.

### V2.4 — OD-aware balance trail

V1.1's `reconcile_balance_trail` uses CR formula (`expected = opening + credit - debit`) universally. **Wrong for OD.**

Per `CLAUDE.md`:
- **Alliance**: balance is positive debt magnitude → trail = `prev + debit - credit`
- **Ambank**: balance is negated → trail = `prev + credit - debit` (CR-style on negated values, equivalent)

Dispatch by `account_meta["convention"]`. When `is_od == True` AND bank is Alliance, use the OD formula. Validation gate: Alliance KYDN should pass 7/7 months instead of 6/7.

### V2.5 — C14/C15 / C21–C23 finalization

- **C14/C15**: keyword fallbacks present (`RETURNED?\s*CHEQ`/`DISHONOURED`) but never empirically validated. Cross-corpus check: do any rows fire? Eyeball them. If broken, fix the regex.
- **C21–C23 monitoring**: V1.1 handles at flag layer (16 indicators in `flags.indicators[]`). Decision: keep flag-layer-only (recommended — schema doesn't reserve C21–C23 fields per-row), or wire per-row tags. Default: keep current; just document in handoff that this is intentional.

---

## Out of scope (V3, follow-up session)

- Anthropic SDK wiring (`pip install anthropic`) for automated narrative
- End-to-end pipeline glue: PDF → `app.py` parser → `kredit_lab_classify` → renderer → final HTML
- Affin OCR-only bank classification
- Counterparty-ledger merging beyond M1–M4 (M5–M7 if undefined)

---

## User-supplied principles (load-bearing)

1. **Older `*.classified.json` references are baseline, NOT ground truth.** They predate Sprint 6 (HLB #4, Bank Rakyat #9, Alliance #2), Rules v3.4 → v3.5, and Prompts v3.5.2 → v3.5.6. Use them as a sanity gate ("did I catastrophically regress?") not a target.
2. **Stay firm where V1.1+ logic is rulebook-correct.** When AI ref disagrees but V1.1 follows `CLASSIFICATION_RULES_v3_5.json` keywords + parser-metadata trust, hold the line. Specific Muhafiz examples: 6× SAMSI BIN IBRAHIM Monthly Instalment rows V1.1 fires C11 (rulebook-correct, AI was inconsistent); 2× BANK FEES bucket rows V1.1 fires C24 (parser metadata, AI over-rode).
3. **Cross-bank only.** No bank-specific code paths. Use existing helpers in `core_utils.py`.
4. **Don't modify** `app.py`, `fraud_app.py`, per-bank parsers, `core_utils.py` (extending is OK).
5. **Schema-validate before write** — `jsonschema.validate(analysis, schema)` is a hard gate.
6. **Don't auto-commit** — user reviews and commits manually.

---

## Files to read (in order)

1. **This file.**
2. **`prompts/CLASSIFIER_HANDOFF.md`** — V1 brief; architecture pointers, hard rules, file map. Still load-bearing.
3. **`prompts/NEXT_CHAT_PROMPT.md`** — last ~400 lines (V1 + V1.1 session handoffs). Has bug fixes and lessons learned.
4. **`kredit_lab_classify.py`** — entire file (~1500 lines). The V1.1 state. Read with focus on:
   - `BUCKET_TO_CATEGORY` (line ~75) and `_KEYWORD_RULES` (line ~95) — extension points for V2
   - `_CATEGORY_SIDES` — already includes C26/C27, just need to wire them
   - `classify_transactions` (line ~340) — add C26/C27 default rule at end of else-chain
   - `build_monthly_analysis` (line ~440) — add cases for C26/C27
   - `build_consolidated` (line ~590) — add `total_trade_income_cr`, `total_trade_expense_dr` if schema requires (check first)
   - `build_top_parties` — apply M1–M4 merging here
   - `_render_decisions_form` + `streamlit_main` — UI changes for V2.2 two-pass flow
5. **`validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json`** — categories C26/C27 (`name`, `side`, `keywords`, `disambiguation`, `description` fields specifically).
6. **`validation runs - json/claude ai prompt file/BANK_ANALYSIS_SCHEMA_v6_3_5.json`** — search for `trade_income` and `trade_expense` to confirm field names + types in `monthly_analysis[]` and `consolidated`.
7. **One trade-heavy `full_report.json`** — pick `Bank Rakyat Koperasi Felcra` (4373 rows, 0% V1.1 classified) or `BIMB Mytutor` (8042 rows, 0%). Look at the top 30 counterparties to inform the C26/C27 default rule audit.
8. **`core_utils.py`** — existing helpers: `_company_root`, `should_drop_as_counterparty`, `determine_account_type`. Extend if needed; don't reimplement.
9. **`CLAUDE.md`** (untracked but exists) — OD balance sign conventions per bank.

---

## Test plan

After V2 lands:

1. **Smoke test**:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from kredit_lab_classify import *
data = load_parser_output('validation runs - json/claude ai prompt file/Full Report Sample/Full Report CIMB Muhafiz.json')
schema = load_schema()
decisions = AnalystDecisions()
acct = detect_account_type(data)
recon = reconcile_balance_trail(data, acct['convention'])
classified = classify_transactions(data, {}, decisions)
monthly = build_monthly_analysis(classified, data, recon)
cons = build_consolidated(monthly)
flags = build_flags(cons, monthly)
analysis = assemble_analysis_json(
    data=data, classified=classified, monthly=monthly, consolidated=cons,
    top_parties=build_top_parties(classified, decisions.related_parties),
    large_credits=build_large_credits(classified),
    own_related=build_own_related_transactions(classified),
    loans=build_loan_transactions(classified),
    flags=flags, observations=build_observations(cons, flags),
    unclassified=build_unclassified(classified),
    parsing_metadata=build_parsing_metadata(data, recon),
    account_meta=acct,
)
validate_against_schema(analysis, schema)
print('OK')
"
```

2. **Cross-corpus regression**: 29/29 must remain schema-valid (use the all-corpus runner pattern from V1.1 session in `prompts/NEXT_CHAT_PROMPT.md`).

3. **Classification-rate uplift**: Muhafiz target 49% → 80%+. Corpus average 10% → 65%+. Files like Bank Rakyat Felcra and BIMB Mytutor (currently 0%) should jump to 70%+.

4. **Eyeball test**: Load any analysis.json into a viewer, scroll the top 20 C26 entities — should be real customer names. Top 20 C27 entities — real suppliers. No own-company / statutory / bank-fee leakage.

5. **OD validation**: Alliance KYDN reconciliation must pass 7/7 months (was 6/7 in V1.1).

6. **RP4 flow**: Streamlit on Muhafiz → gate surfaces 3 candidates → check 2 → re-classify → verify those rows now show `primary: "C04"` in `unclassified_transactions` is empty for those names.

7. **Live UI**: `streamlit run kredit_lab_classify.py` → upload Muhafiz → click through → all three downloads work, two-pass flow doesn't lose state.

---

## First actions in the new session

1. Read this file + V1 handoff.
2. Run V1.1 smoke test (above) — confirm starting point.
3. **Audit C26/C27 default rule first** — load `Full Report Bank Rakyat Koperasi Felcra.json`, list top 30 unclassified counterparties, eyeball whether they're customers/suppliers (yes → ship default rule; no → use keyword variant).
4. Implement V2 in this order (smallest blast radius first):
   - V2.4 OD balance trail (1 function change)
   - V2.5 C14/C15 validation + C21–C23 doc decision
   - V2.1 C26/C27 trade rules (the big one — schema fields + classify + monthly agg + consolidated)
   - V2.3 M1–M4 counterparty merging
   - V2.2 RP4 confirmation flow (most UI churn — last)
5. After each step: schema-validate Muhafiz + cross-corpus regression. Don't batch.
6. Commit as `Sprint 5 #21 V2: <theme>` per V1's commit-message style.
7. Append session handoff to `prompts/NEXT_CHAT_PROMPT.md`.

---

## Rollback

```
# Drop V2 only (return to V1.1):
git reset --hard d900f03

# Drop V2 + V1.1 (return to V1):
git reset --hard bfda34c

# Nuclear: drop everything (return to pre-classifier state):
git reset --hard c45b3ce
```

---

## Context budget

V1 build: ~90k tokens. V1.1: ~30k. V2 will probably need 70–90k:
- Phase A — corpus audit + schema field check + RP4 UI sketch: ~15k
- Phase B — implement V2.1 + V2.4 + V2.5 + cross-corpus validate: ~30k
- Phase C — V2.3 merging + cross-corpus validate: ~15k
- Phase D — V2.2 two-pass UI + manual UI test: ~15k
- Phase E — commit + handoff append: ~10k

Single fresh session recommended. Don't try to bundle V3 (SDK) into V2.
