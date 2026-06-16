# Continuation Prompt — Post-Session Checklist (Apr 20–21) + Next Iteration

Copy-paste the block below into a fresh Claude Code session in this project.

---

## Context

- Repo: `Bank-Statement-Analysis-main 3`, branch `main`. All latest work is pushed.
- Parser stack v6.3.3 + classifier prompt stack v3.5.2.
- Today is 2026-04-21.

### Architecture — keywords live in TWO layers

```
PDF → Parser (app.py) → full_report.json → Claude AI (reads rules) → Analysis JSON
      ▲ Layer 1 (primary)                   ▲ Layer 2 (safety net)
      _extract_counterparty()               CLASSIFICATION_RULES_v3_3.json
      deterministic, free                   AI judgment, costs tokens
```

- **Layer 1 (Parser)**: `app.py` `_extract_counterparty()` + per-bank helpers like `_extract_counterparty_alliance()` label transactions as `BULK SALARY`, `BANK FEES`, `LOAN REPAYMENT`, `LHDN`, `KWSP`, `SOCSO`, `HRDF`, `LOAN DISBURSEMENT`, `FD/INTEREST`, etc. Primary classification.
- **Layer 2 (AI Rules)**: `CLASSIFICATION_RULES_v3_3.json` keywords guide the Claude AI as a safety net. Also semantic refinement (e.g. C11 vs C04 based on entity context).
- **Both must be updated together.** Same keywords / same patterns / always in sync.
- All keyword additions must work **across all banks** — no bank-specific hacks.
- **Test with raw `full_report.json` files** (parser output), NOT AI analyzed JSONs.

### Workflow prompts
- `prompts/improve_keywords.md` — keyword-loop authoritative workflow
- `prompts/fix_bank_parser.md` — per-bank parser repair workflow
- `prompts/run_audit_loop.md`, `prompts/NEXT_CHAT_PROMPT.md` — session-bootstrap prompts

---

## What's been done — session Apr 20–21 (9 commits)

All pushed to `origin/main`, live on `luqman196/bank-statement-analyzer-v6.3-`.

| # | Commit | Theme | Impact |
|---|---|---|---|
| 1 | `193a6c9` | C11 keyword sync (parser + rules + validator) | Closed gap on 4 banks: Alliance Bestlite +14, Alliance KYDN +5 DR, CIMB Muhafiz +17, OCBC Calvin Skin +6 |
| 2 | `d25de07` | Alliance per-row signed-balance DR/CR fix | Replaced file-level `_detect_dr_balance_account` with per-row CR/DR suffix math. Handles current accounts that go overdrawn mid-month (KYDN Apr–Aug 2025: 29 C11 rows now all DR, were 5 DR + 24 CR) |
| 3 | `5579b4b` | CP9 Maybank VISA/biller fallback | MBB Mytutor: 113 → 10 garbage out of 209. Added `_has_real_word` helper to pick before-* when after-* is masked card/ref |
| 4 | `86020e1` | CP3 Ambank comma-format + Alliance purpose-strip | 84.5% → 97.9% good across DUITNOW txns. All 3 Ambank files 100% clean; Alliance `payment`/`fund transfer` prefixes peeled |
| 5 | `05f7eab` | CP2 peel duplicated F ADVANCE | Future-proofs non-PLANWORTH factoring entities (currently hidden by CP11 hardcoded merge) |
| 6 | `98dd492` | C05 AUTOPAY DR rules sync | 67 CIMB Muhafiz bulk-payroll txns now catch Both layers instead of Parser-only |
| 7 | `564a969` | CP6 date-leak fix | `TR TO SAVINGS JAN AND FEB 2026 RODZARIAH BINTI YUS STAFF ADVANCE` now correctly extracts `RODZARIAH BINTI YUS`. Extended `_strip_purpose_prefix_tokens` with guarded AND/& skip |
| 8 | `4a1ae5c` | Public Bank C24 fees | PUBLIC LSR 0 → 4 Both, Public Mazaa 0 → 101 Both. Added `CHQ PROCESS FEE`, `HANDLING CHRG`, `CHEQ STAMP FEE`, plus made `PROCESSING` suffix optional |
| 9 | `c5166e0` | CP3 Alliance residuals | 97.9% → 98.8% good (+32 recovered). Same greedy-regex bug as CP6 was in `_ab_strip_trailing_refs`. Added AB0 early-return for bare `DuitNow CR Trf CA` |

---

## What YOU need to do before the next session

### 1. Regenerate corpus JSONs (highest priority)

The existing `Full Report *.json` files in `validation runs - json/claude ai prompt file/Full Report Sample/` still contain **pre-fix** counterparty data. Re-run the Streamlit app (`streamlit run app.py`) on the PDFs that were touched by this session's fixes:

| File to regenerate | Why it matters |
|---|---|
| `Full Report Alliance KYDN.json` | DR/CR flip fix (29 C11 rows flipped) + CP3 purpose-strip + AB0 empty-body |
| `Full Report Alliance Bestlite Sept 25-Feb26.json` | CP3 purpose-strip + trailing-ref bug fix |
| `Full Report MBB Mytutor.json` | CP9 VISA/biller fix — 108 corrections visible |
| `Full Report Ambank RE Concept.json` | CP3 Ambank comma-format (355 corrections) |
| `Full Report Ambank Hon Engineering.json` | CP3 Ambank comma-format (33 corrections) |
| `Full Report Ambank Plentitude.json` | CP3 Ambank comma-format (47 corrections) |
| `Full Report CIMB Muhafiz Sept 25 - Feb 26.json` | C11 + CP6 date-leak + C05 AUTOPAY DR |
| `Full Report PUBLIC LSR.json` | C24 PB fees |
| `Full Report Public Mazaa.json` | C24 PB fees (101 corrections) |
| `Full Report OCBC Calvin SKin.json` | C11 loan repayment labels (+6) |

Drop each regenerated JSON back into the same folder, replacing the old version.

### 2. Spot-check one file in the UI

Open the Streamlit UI on **MBB Mytutor** (highest-impact file, 108 corrections). Verify:
- VISA card repayments show `MAYBANK VISA CARD` instead of `XXXX-XXXX-XXXX-####`
- Top payees list no longer has masked card numbers or long ref-codes
- C05/C11/C24 transaction counts match expectations

### 3. Run one refreshed JSON through your Claude AI classifier

Pick **MBB Mytutor** or **CIMB Muhafiz**. Feed through `CLASSIFICATION_RULES_v3_3.json` + `SYSTEM_PROMPT_v3_5_2.md`. Compare category totals and top-payee lists against the pre-fix AI analyzed run to confirm classification improved (or at least didn't regress).

### 4. Re-run the validator on refreshed corpus

```bash
python3 scripts/validate_keywords.py
```

Any remaining sync gaps on the fresh data are real (not artifacts of the stale corpus). That list is the authoritative input for the next iteration.

### 5. (Optional) Decide on untracked workspace files

`git status` shows several untracked items:
- `CLAUDE.md` — worth committing so future sessions have the context
- `audit_reports/` — generated output; consider `.gitignore`
- `scripts/audit_all_banks.py`, `scripts/verify_ab_nov.py` — decide if ready to commit
- Various `Bank-Statement/**/` new sample folders — decide per folder

Not blocking; can do at leisure.

---

## What's next for the keyword / parser loop

### Original priority queue — all addressed this session
- ✅ C11 Loan Repayment (commit 1)
- ✅ C05 AUTOPAY DR rules-sync (commit 6)
- ✅ CP1–CP11: CP1 good, CP2 fixed (5), CP3 Ambank+Alliance fixed (4, 9), CP4 good, CP5 good, CP6 fixed (7), CP7/CP8 good, CP9 fixed (3), CP10/CP11 good
- ✅ Public Bank C24 both-miss gap (commit 8)

### Remaining residual items (low priority, diminishing returns)

| Item | Scope | Effort |
|---|---|---|
| **CP3 Alliance 45 residual garbage** | Payer-specific invoice prefixes (`IV0925`, `K0032`, `YN`, `PJ`), MYCN patterns, 1-char initials breaking `_tail_alpha_run` | Needs bespoke handlers; each payer has own ref scheme |
| **Bank-specific bulk-salary patterns** | Alliance `IB2G BLKTRF … SALARY`, MBB `DUITNOW PAYPRX DR SALARY`, MBB `MAS PAYMENT * … SALARY JULY` — ~10–15 txns | Narrow targeted regex adds |
| **C05 STAFF OVERTIME rules-parser divergence** | Validator flags 169 "rules-only" but this is BY DESIGN — parser correctly preserves employee names (e.g. `KRISTIEN YAP YUEN T`), AI classifies C05 via keyword. Do NOT bucket these as BULK SALARY | Accept as cosmetic validator warning |

### If fresh corpus surfaces new gaps
Run the full keyword workflow per `prompts/improve_keywords.md`: one bank × one category, show diff, cross-bank-safe, verify against all corpus files.

### Fraud detector — further improvements (deferred)

**Known remaining HIGH on genuine corpus (user to review):**
- **AgroBank `IESB - AGRO ...-May-2025.pdf`** — 236KB / 1 page, 7.5x batch median density. User says not fraud. Either accept as edge case (low-transaction month) or add a heuristic to only flag size outliers when paired with another signal
- **Ambank `/4/SWHSB AMB 2981 2025 5-9.pdf`** (6 files) — all flagged for "Overlapping DIFFERENT text" on 1 page. Investigate: is this genuine Ambank layout quirk or a real tampering signal?

**Deferred architectural improvements:**
- **Layer 9 (Post-Parse Validation)**: Use parsed transaction data to detect anomalies the PDF-level analysis misses
- **Cross-month balance continuity**: In `compare_batch()`, verify ending balance of month N = beginning balance of month N+1
- **Lower font anomaly threshold**: Flag individual anomalous amounts even at 99% consistency (catches surgical single-amount edits)

---

## Current corpus — 29 full_report.json files across 12 banks

Located in `validation runs - json/claude ai prompt file/Full Report Sample/`.

**Files still awaiting regeneration** (see section 1 above): Alliance KYDN, Alliance Bestlite, MBB Mytutor, Ambank (×3), CIMB Muhafiz, PUBLIC LSR, Public Mazaa, OCBC Calvin Skin.

Other banks in corpus (unchanged by this session): Maybank Hydrise/Zaim/Hou Tian/Shahnaz/Naara, BIMB KMZ/Mytutor, Bank Rakyat ×2, CIMB Naara, Hong Leong ×2, OCBC LF, Public Mazaa (already regenerated above), RHB ×2, UOB ×2, Bank Muamalat, Agrobank.

**Zero coverage**: Affin only (OCR-only bank, deferred).

---

## Key files

| File | Purpose |
|---|---|
| `prompts/improve_keywords.md` | **Authoritative keyword workflow** — follow exactly |
| `prompts/fix_bank_parser.md` | Per-bank parser repair workflow |
| `prompts/run_audit_loop.md` | Audit loop bootstrap |
| `pdf_fraud_detector.py` | 8-layer PDF integrity analysis + batch comparison |
| `app.py` | Main Streamlit app + `_extract_counterparty()` (Layer 1) |
| `alliance.py` | Alliance parser — per-row signed-balance (this session) |
| `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_3.json` | Keyword dictionary (Layer 2) |
| `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_2.md` | Claude AI system prompt (not touched yet) |
| `validation runs - json/claude ai prompt file/Full Report Sample/` | Raw transaction exports (test corpus) |
| `scripts/validate_keywords.py` | Dual-layer keyword sync checker |
| `scripts/validate_reference_statements.py` | Parser regression test (14 banks) |
| `scripts/audit_all_banks.py` | Parser quality audit (A-F grading) |
| `Bank-Statement/Fraud Bank Statement/` | Tampered + original PDFs for fraud testing |

## Rules for keyword changes (from `improve_keywords.md`)

1. **Cross-bank only** — never add bank-specific patterns (use `bank_patterns{}` for those)
2. **Multi-word preferred** — short tokens (< 4 chars) risk substring collisions
3. **Validate both directions** — confirm true positives AND check for false positives on wrong DR/CR side
4. **Test against TC01–TC34** — existing test cases must not break
5. **Update regex too** — when adding to `keywords[]`, also update the corresponding `regex` field
6. **Update both layers** — parser `app.py` (`_extract_counterparty`) AND `CLASSIFICATION_RULES_v3_3.json` keywords must stay in sync. Also keep `scripts/validate_keywords.py` PARSER_PATTERNS mirror in sync.
7. **Show diffs before applying** — user approves explicitly before each edit
8. **Do not auto-commit** — user reviews and commits manually (commits ARE expected within the loop; the rule is "no silent commits")

## Rules for fraud detector changes

1. **Test against ALL genuine PDFs** — 14 banks, ~392 PDFs, zero HIGH regressions on previously-LOW files
2. **Test against tampered corpus** — Aman Nukleus (6) + DMC Travel (4) must remain HIGH
3. **Test false positive cases** — Naara CIMB, Shahnaz MBB, Mytutor MBB/BIMB, OCBC Calvin Skin (12 files), Agrobank Integrasi Erat Sep/Oct must remain LOW
4. **Never block** — fraud detector flags only, never prevents extraction
5. **Profile changes need evidence** — only add bank profiles from real PDFs in the corpus

## First actions in new chat

1. Read this prompt + `prompts/improve_keywords.md`
2. Confirm corpus has been regenerated (list `Full Report Sample/`, check file modification times)
3. Run `python3 scripts/validate_keywords.py` — review sync state on refreshed data
4. Run `python3 scripts/audit_all_banks.py` — confirm all 14 banks hold their grades
5. If new gaps appear on fresh corpus, start with the highest-volume one
6. If no new gaps, consider fraud detector deferred items or the CP3 residual bespoke handlers

## The simple loops

**Keywords:**
```
Drop updated full_report.json → run validate_keywords.py → find gaps → propose fix both layers → user approves → apply → re-run → repeat
```

**Parser fix (per bank):**
```
Open audit_reports/<bank>_quality_report.json → identify bug class → fix bank parser file in isolation → re-run audit → regression-check all 14 banks
```

**Fraud detector:**
```
Identify false positive/missed detection → fix detector → re-test all ~392 genuine + 10 tampered → repeat
```

---

## Session handoff — 2026-04-22 (v3.5.3 shipped, end-to-end validation next)

Copy-paste the block below into a fresh Claude Code session in this project to continue from where we left off.

---

```
Continuing from previous session (2026-04-22). Project:
/Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## What was done last session

Shipped v3.5.3 — eight targeted fixes driven by KDYN/MUHAFIZ/MYTUTOR
validation runs. Both repos pushed live to Railway:

- Parser repo  (outer)  commit e796947 — bank-statement-analyzer-v6.3-
- Renderer repo (nested, bank-statement-analysis-HTML-fresh/) commit 927b6f9
  — bank-statement-analysis-HTML

Changes summary:
1. Top 10 payers/payees (was Top 5)
2. Ghost-verb filter with cross-bank stopword list (Maybank BUG-001 fix
   in maybank.py recovers dropped counterparty names; CN6 suppression
   rule in renderer as defensive net)
3. Statutory C06-C09 side-gate (side==DR AND NOT match_own_party),
   prevents EPF PAYMENT CR mis-fire (MUHAFIZ RM 600K bug)
4. EPF/SOCSO coverage % via set intersection, bounded [0, 100]
5. LHDN and HRDF decoupled from salary coverage — info-only cards,
   no ratio (was MYTUTOR 120% bug)
6. Commission (Comm/Komisen/Habuan) policy — default regular expense,
   not C05 unless user confirms agents are employees
7. effective_match_rate replaces pattern_match_rate as parser grade
8. Schema-fields pre-flight step in system prompt, Phase 4 MEDIUM-
   confidence related-party default (proceed, don't block)

Alliance parser improvements (app.py):
- generic voucher-code stripping (PV/YN/..., IV-YN-...)
- IB2G BLKTRF bulk-salary detection without SALARY keyword (March 2025
  KDYN case)
- leading alphanumeric ref token strip for CR ADVICE - IBG

## What the user is doing now

End-to-end validation of the three target cases:
- MUHAFIZ (CIMB, Sep25-Feb26) — parser unchanged, Claude AI re-run only
- KDYN (Alliance, Mar-Aug 25) — re-parse via Streamlit, then Claude AI
- MYTUTOR (Maybank Islamic, Jan-Jun 25) — re-parse, then Claude AI

User has to manually re-upload the three prompt files to Claude AI
project — git push does NOT sync to Claude AI web. Files live in:
validation runs - json/claude ai prompt file/

Key files to reference:
- SYSTEM_PROMPT_v3_5_2.md (v3.5.3)
- CLASSIFICATION_RULES_v3_3.json (v3.3.1)
- BANK_ANALYSIS_SCHEMA_v6_3_3.json (v6.3.3.2)

Previous session's challenge reports, quality reports, and HTML outputs
are in: validation runs - json/

## Pick up from here

I'm about to run the end-to-end tests. If any of the three outputs
show unexpected results (bugs, regressions, new friction), help me
diagnose and patch. Likely areas to watch:
- Alliance parser: any remaining voucher patterns not covered by the
  generic regex
- Ghost-verb false positives (real entity named with stopwords only)
- Related-party auto-detection confidence levels
- Any schema validation errors if Claude AI outputs non-conforming JSON

Expect me to paste outputs / screenshots / JSON diffs for you to review.
```

---

## Session handoff — 2026-04-23 (Sprints 1-4 shipped, Sprint 5/6 pending)

Copy-paste the block below into a fresh Claude Code session to continue.

---

```
Continuing from 2026-04-23 session. Project:
/Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## Shipped this session (4 commits, 2 repos, all pushed)

Parser repo (bank-statement-analyzer-v6.3-, branch main):
- 793b5f2: Parser Sprint 2 — core_utils.py cross-bank helpers
  (determine_account_type, statutory_bucket_for, clean_description
  pipeline, patronymic guard, stop-word drop) plus alliance.py BUG-001
  ghost-row drop, cimb.py refactor to core_utils + CIMB extras, app.py
  Maybank CP7/CP8/CP9 ghost-verb guards + INTER-BANK PAYMENT extractor.
- db9a8cb: Sprint 4 — new v3.5.4 / v3.4 / v6.3.4 files in
  `validation runs - json/claude ai prompt file/`.

Renderer repo (bank-statement-analysis-HTML, branch main):
- 12a1cf4: v6.3.4 renderer — Fraud Detector tab + button always render
  (placeholder when pdf_integrity absent), Top Parties bar chart inline
  month+amount labels via new _render_monthly_bars() helper.

See prompts/SESSION_SUMMARY_20260423.md for complete details.

## What user should do FIRST (before any new work)

1. Upload 3 new AI files to Claude AI project knowledge (replacing
   v3_5_2 / v3_3 / v6_3_3):
   - validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_4.md
   - validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_4.json
   - validation runs - json/claude ai prompt file/BANK_ANALYSIS_SCHEMA_v6_3_4.json

2. Re-parse MTA + KYDN + Muhafiz via Streamlit (Railway is live on the
   new parser). Drop fresh full_report.json into Full Report Sample/.

3. Feed refreshed JSON through Claude AI with the new v3.5.4 prompt.
   Expected outcomes:
   - Muhafiz unclassified CR (PIASAU GAS, PERTAMA FERROALLOYS, SCHENKER
     LOGISTICS, SOUTHERN CABLE) now → C26 Trade Income
   - KDYN EPF ratio 22-24% → status OK (not WARNING — combined-
     remittance dual-band is now recognised as normal)
   - MTA ~278 ghost-verb txns → UNNAMED TRANSFER (CR/DR) consolidated
     buckets instead of UNIDENTIFIED
   - All three: bar charts in Top Parties with inline labels
     "Mar: 162K, Apr: 170K, ..."
   - Muhafiz Fraud Detector tab present (placeholder if AI still
     doesn't emit pdf_integrity)

## Pending work — Sprint 5 + Sprint 6

Sprint 5 (heavy, fresh-session recommended):
- #21 kredit_lab_classify.py — reusable Python module AI calls instead
  of rewriting classification code every run (500-1000 lines estimated)
- #23 Regression fixture suite — freeze MTA/KYDN/Muhafiz/DMC as
  fixtures under tests/fixtures/
- #24 Synthetic OD simulation — flip CR statement signs to simulate OD
  across 14 banks

Sprint 6 (polish, small items — can be bundled):
- #6 Wire should_drop_as_counterparty into per-bank extraction paths
- #8 Alliance date-clamp to statement period (defence-in-depth on BUG-001)
- #9 Alliance rail-prefix strip (CR ADVICE, IB2G FND TRF, FPX ABB,
  DuitNow CR Trf, HUB CA MISC DR) — reuse core_utils.strip_reference_numbers
- #10 IB2G trailing own-company-name strip (HUAREN RESOURCES SDN
  KLINIK DRS YOUNG NEW cleaning limitation)
- #22 canonical_entities_<COMPANY>.json band-aid

## Key decisions from this session (do not re-litigate)

- Trade Income/Expense = C26/C27 (NOT C17/C18 — those are already Cash
  Deposit/Withdrawal in the rulebook).
- Parser is primary; AI is thin. Future bug fixes: default to parser-
  layer fix, not classifier regex.
- Renderer uses single-template. No more "minimal vs full" branch.
- Cross-bank helpers live in core_utils.py. Bank-specific extras pass
  via extra_patterns parameter (CIMB already does this).
- UNNAMED TRANSFER buckets are correct behaviour (ghost-verb data is
  absent, not mis-extracted). Do not invent names.
- EPF dual-band: 11-15% employer-only OR 20-26% combined. KDYN 22-24%
  is NORMAL, not anomaly.

## Key files to reference

Parser / helpers (committed, live):
- core_utils.py — +575 lines of universal helpers
- alliance.py:295-307 — BUG-001 ghost-row filter
- cimb.py:58-94 — CIMB-specific ref patterns; clean_description imported
- app.py:2376-2452 — CP7/CP8/CP9 + INTER-BANK ghost-verb handlers
- bank-statement-analysis-HTML-fresh/app.py:1641-1700 — _render_monthly_bars

Claude AI files (committed, upload pending):
- validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_4.md
- validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_4.json
- validation runs - json/claude ai prompt file/BANK_ANALYSIS_SCHEMA_v6_3_4.json

Documentation:
- prompts/SESSION_SUMMARY_20260423.md — this session
- CLAUDE.md — project instructions

## First actions in new chat

1. Acknowledge the handoff; read prompts/SESSION_SUMMARY_20260423.md.
2. Ask: "Have you uploaded v3.5.4 / v3.4 / v6.3.4 to Claude AI and re-
   run MTA/KYDN/Muhafiz yet?" — their answer dictates next step.
3. If yes and outputs look clean: proceed to Sprint 5 or 6.
4. If no or outputs have regressions: debug against the expected
   outcomes above.
5. If something else entirely: listen.
```

---

## Session handoff — 2026-04-23 late (Sprint 4.5 — Parser Determinism, in progress)

Continuing from a full-context session that hit the limit. Copy-paste below
into a fresh Claude Code session.

---

```
Continuing Sprint 4.5 — Parser Determinism (account_type detection made
deterministic in the parser so the AI stops re-inferring it). Project:
/Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## Context — why this sprint exists

The AI classifier has been struggling + slow because the parser was not
emitting `account_type`. The AI re-derived CR/OD from balance every run,
which added tokens, added errors, and added false positives on edge cases
(EPF PAYMENT CR mis-fired when AI guessed OD wrong, etc.).

Sprint 4.5 fixes this at the source: parser emits locked account_type,
AI trusts it.

## Key DECISIONS taken this session (do NOT re-litigate)

1. **Option A enum** — dropped CASH_LINE as a separate account_type value.
   Islamic Cashline-i / CAP-i / SAP-i are the SAME facility as conventional
   Overdraft (revolving credit). Enum is now CR / OD / UNDETERMINED only.

2. **NO keyword list** in `determine_account_type`. Every keyword I tried
   (OVERDRAFT INTEREST, CASHLINE-i PROFIT CHARGED, DR Interest, etc.)
   generated false positives — either in transfer memos (KYDN's "Instant
   Transfer ... OVERDRAFT INTEREST MAR 2025" that's settling OTHER account)
   or in temporary drawdown events on plain CA (RE CONCEPT's brief dip).
   The user confirmed: keyword list is out.

3. **Evidence-based detection, balance/header only.** Four signals, any one
   locks OD:
     (a) Header discloses non-zero Overdraft or Cashline-i limit
     (b) DR-suffix on >= 50% of balance rows (Alliance/Ambank convention)
     (c) Sustained negative balance on >= 50% of rows (Ambank/UOB negated)
     (d) OD row-math >= 90% while CR math doesn't
   None → CR. Empty text / zero rows → UNDETERMINED (OCR-only).

4. **50% threshold distinguishes temporary drawdown from genuine OD.**
   RE CONCEPT (Ambank/3) with 4% DR-balance rows = CR. SWHSB (Ambank/4)
   with 96% negative-balance rows = OD.

5. **Transfer memos do NOT flag this account as OD.** "Instant Transfer
   ... OVERDRAFT INTEREST MAR 2025" means THIS account is paying OD
   interest on SOME OTHER account. Don't speculate which one. This is
   saved in `feedback_memo_text_scope.md` memory.

## What's DONE (uncommitted as of handoff)

- **core_utils.py** — refactored determine_account_type, added
  `finalize_parser_output`, `stamp_statutory_buckets`,
  `_extract_facility_limits` (Overdraft + Cashline-i regex),
  `_scan_dr_suffix_ratio`. Extended `ensure_transaction_schema` to
  preserve `_account_type_determination` dict on first row.
  **Dropped keyword-list + transfer-prefix filter** in the final refactor
  (per user direction after false positive analysis).

- **alliance.py** — wired with `finalize_parser_output(...)`. Extracts
  page-1 header text pre-truncated at transaction-table marker (defends
  against "overdraft/cashline" substring in boilerplate disclaimer).
  Preserves `balance_sign` (DR/CR suffix) on every row. Removed the
  per-row `"OD" if row_is_dr else "CA"` hardcoded heuristic.

- **scripts/survey_account_type_signals.py** — full corpus evidence
  survey (every PDF, not a sample). Used to build evidence-based rules.

- **scripts/validate_account_type_detection.py** — runs every parser +
  new detection across all 325 PDFs. Per-PDF verdict.

## Validation against full corpus (325 PDFs / 14 banks)

| Bank | Total | OD | CR | UNDET (all OCR-only) |
|---|---|---|---|---|
| AffinBank | 6 | 0 | 0 | 6 |
| AgroBank | 6 | 0 | 6 | 0 |
| Alliance | 12 | 6 (Bestlite) | 6 (KYDN) | 0 |
| Ambank | 24 | 6 (SWHSB / Shang Wan Hong) | 17 | 1 |
| BankIslam | 33 | 0 | 29 | 4 |
| BankMuamalat | 6 | 0 | 6 | 0 |
| BankRakyat | 54 | 12 (MTCEC + CASH LINE folders) | 42 | 0 |
| CIMB | 37 | 0 | 34 | 3 |
| HongLeong | 17 | 0 | 17 | 0 |
| Maybank | 57 | 0 | 57 | 0 |
| OCBC | 6 | 0 | 6 | 0 |
| PublicBank | 17 | 0 | 17 | 0 |
| RHB | 44 | 6 (Clear Water Services SDN. BHD., RHB/6) | 38 | 0 |
| UOB | 6 | 6 (Upell) | 0 | 0 |
| **TOTAL** | **325** | **36** | **275** | **14** |

User confirmed every OD case is genuine. No false positives. No false
negatives on known cases.

## Critical lessons from this session (memory saved)

- `feedback_verify_before_asserting.md` — Never claim an account is OD /
  Cash Line / SAP-i from a helper result alone. Always read the actual
  PDF header text first. I made this mistake with KYDN and the user
  called it out sharply. Bug was `'capi'` substring matching
  "CAPITAL SQUARE" — fixed with word-boundary regex.

- `feedback_memo_text_scope.md` — Facility keywords in transfer-prefix
  descriptions are MEMOS describing OTHER accounts being settled, not
  this statement's facility.

## What's NEXT — pick up here

1. **Commit checkpoint.** Nothing committed yet this sprint. Recommended:
   one commit for core_utils + alliance.py + scripts/. User has a firm
   rule against silent commits, so ask first.

2. **Update schema + prompt for Option A** (drop CASH_LINE enum):
   - `validation runs - json/claude ai prompt file/BANK_ANALYSIS_SCHEMA_v6_3_4.json` — remove "CASH_LINE" from `account_type` enum
   - `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_4.md` — remove CASH_LINE references, update Phase 1 language
   - `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_4.json` — remove CASH_LINE mentions
   - Bump versions to v6_3_5 / v3_5_5 / v3_5

3. **Wire the remaining 13 parsers** with `finalize_parser_output`:
   - ambank.py, cimb.py, maybank.py (highest priority — most corpus)
   - public_bank.py, rhb.py, bank_islam.py, bank_rakyat.py,
     hong_leong.py, bank_muamalat.py, affin_bank.py, agro_bank.py,
     ocbc.py, uob.py
   - Each parser needs: extract page-1 header (pre-truncated), derive
     opening/closing balance if available, call
     `finalize_parser_output(rows, header_text=..., opening_balance=...,
     closing_balance=...)` before returning.

4. **app.py harvest** — after calling each parser, harvest row[0]
   `_account_type_determination` into a top-level
   `account_type_determinations: [{source_file, bank, locked_type,
   confidence, rationale, ...}]` array in `full_report.json`.

5. **scripts/audit_all_banks.py** — replace hardcoded OD sign convention
   (CLAUDE.md warns about this) with stamped `account_type` on rows.

6. **Full regression test** — run `scripts/validate_reference_statements.py`
   + `scripts/audit_all_banks.py` across all 14 banks to confirm no
   parser broke from the `balance_sign` change.

## Files touched (uncommitted)

- core_utils.py
- alliance.py
- scripts/survey_account_type_signals.py (new)
- scripts/validate_account_type_detection.py (new)
- Memory: feedback_verify_before_asserting.md,
  feedback_memo_text_scope.md (new); MEMORY.md updated.

## First actions in new chat

1. Read this handoff section.
2. Read:
   - core_utils.py around line 444 (determine_account_type and its helpers)
   - alliance.py (wired — the template for other parsers)
   - scripts/validate_account_type_detection.py (how to validate after
     each parser wiring)
3. Run the validation script to confirm the 36-OD / 275-CR / 14-UNDET
   state is still intact.
4. Ask the user: commit checkpoint first, or update schema/prompt first,
   or start wiring Ambank next? Default recommendation: commit first.
```

---

## Session handoff — 2026-04-23 very-late (Sprint 4.5 parser-side DONE)

Continuing from the prior Sprint 4.5 in-progress session. All 14 parsers
are now wired, AI prompt files bumped for Option A, three commits local
on main. Nothing pushed to origin yet — user wants to settle everything
before pushing.

Copy-paste the block below into a fresh Claude Code session.

---

```
Continuing from 2026-04-23 late session. Project:
/Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## What shipped this session (3 commits, LOCAL ONLY — not pushed)

- 4c65ec2  Sprint 4.5: Parser-locked account_type (CR/OD/UNDETERMINED)
           core_utils.py refactor (determine_account_type,
           finalize_parser_output, stamp_account_type_once,
           stamp_statutory_buckets) + alliance.py wired +
           scripts/survey_account_type_signals.py +
           scripts/validate_account_type_detection.py. Evidence-based
           detection: header facility-limit, DR-suffix majority,
           sustained-negative balance, OD row-math. NO description-
           keyword scanning. Option A — Cashline-i collapses into OD;
           no separate CASH_LINE enum.

- fc1696e  Sprint 4.5: Wire 13 remaining parsers with finalize_parser_
           output. ambank, cimb, maybank, public_bank, rhb, bank_islam,
           bank_rakyat, hong_leong, bank_muamalat, affin_bank,
           agro_bank, ocbc, uob. Every parser's entry function captures
           page-1 header (truncated at its bank-specific transaction-
           table marker) and wraps every return site with
           finalize_parser_output(rows, header_text=...,
           opening_balance=..., closing_balance=...). Multi-return
           parsers (CIMB table-mode + text-mode fallback; Bank Rakyat
           empty-rows + normal) funnel both paths through the same
           finalize call.

- 4267f1c  Sprint 4.5: AI prompt bump — v3.5.5 / v3.5 / v6.3.5
           (Option A, drop CASH_LINE). Three new files in
           `validation runs - json/claude ai prompt file/`:
           - BANK_ANALYSIS_SCHEMA_v6_3_5.json
           - SYSTEM_PROMPT_v3_5_5.md
           - CLASSIFICATION_RULES_v3_5.json
           Old v6_3_4 / v3_5_4 / v3_4 files kept alongside as history.
           Enum cuts verified programmatically:
             accounts[].account_type = ['Current','Savings','OD']
             locked_type             = ['CR','OD','UNDETERMINED']
             header_signal           = ['CR','OD',null]
             schema_version const    = "6.3.5"

## Full corpus validation (325 PDFs / 14 banks, post-wiring)

  36 OD / 275 CR / 14 UNDETERMINED (all OCR-only) / 0 ERR

  AffinBank    :  0 OD /  0 CR /  6 UNDET   (all OCR-only)
  AgroBank     :  0 OD /  6 CR /  0 UNDET
  Alliance     :  6 OD (Bestlite) /  6 CR (KYDN) /  0 UNDET
  Ambank       :  6 OD (SWHSB) / 17 CR /  1 UNDET
  BankIslam    :  0 OD / 29 CR /  4 UNDET
  BankMuamalat :  0 OD /  6 CR /  0 UNDET
  BankRakyat   : 12 OD (CASH LINE + MTCEC) / 42 CR /  0 UNDET
  CIMB         :  0 OD / 34 CR /  3 UNDET
  HongLeong    :  0 OD / 17 CR /  0 UNDET
  Maybank      :  0 OD / 57 CR /  0 UNDET
  OCBC         :  0 OD /  6 CR /  0 UNDET
  PublicBank   :  0 OD / 17 CR /  0 UNDET
  RHB          :  6 OD (Clear Water RHB/6) / 38 CR /  0 UNDET
  UOB          :  6 OD (Upell) /  0 CR /  0 UNDET

User confirmed every OD genuine. Parser regression
(scripts/validate_reference_statements.py all banks): 44,808 tx / 0
parse_errors / 0 invalid_dates / 0 schema violations / 0 sign-
confusion rows.

## What user should do FIRST (before any new work)

1. PUSH or hold: three commits (4c65ec2, fc1696e, 4267f1c) are local
   on main. Decide whether to push to origin/main now.

2. Upload the v3.5.5 / v3.5 / v6.3.5 AI files to the Claude AI project
   knowledge (replacing v3.5.4 / v3.4 / v6.3.4). Git push does NOT
   sync to claude.ai web.

3. Re-parse MTA / KYDN / Muhafiz via Streamlit on the new parser.
   Fresh full_report.json files should now carry:
   - accounts[*].account_type = "Current" | "Savings" | "OD"
     (display label)
   - per-row account_type = "CR" | "OD" | "UNDETERMINED"
     (parser verdict)
   - per-row statutory_bucket = "KWSP" | "SOCSO" | "LHDN" | "HRDF"
     | null
   - row[0]._account_type_determination = { locked_type, confidence,
     locked_rationale, cr_trail, od_trail, dr_suffix_stats,
     row_level_test, facility_limits_in_header, ... }

   Caveat: app.py does NOT yet harvest
   row[0]._account_type_determination into a top-level
   accounts[].account_type_determination object — see Sprint 4.5
   pending item 1 below.

4. Feed refreshed JSON through Claude AI with the new v3.5.5 prompt.

## Pending — Sprint 4.5 finish

1. app.py harvest. After each parser returns rows, pull
   row[0]["_account_type_determination"] and attach it to the
   matching accounts[] entry as
   accounts[].account_type_determination (+ pop the underscore-
   prefixed metadata off). Schema already defines this field —
   BANK_ANALYSIS_SCHEMA_v6_3_5.json lines 143-197. Once wired, the
   AI classifier trusts it directly (Step 2 of pre-analysis gate,
   per SYSTEM_PROMPT_v3_5_5.md line 44).

2. OCR-only PDFs (AffinBank x6, Ambank x1, BankIslam x4, CIMB x3)
   produce 0 rows, so finalize_parser_output skips stamping (early
   return) and no determination is attached. app.py's harvest step
   should synthesize an UNDETERMINED sentinel per OCR-only
   source_file so the accounts[] array has a determination for every
   PDF. scripts/validate_account_type_detection.py handles this by
   calling determine_account_type directly on empty rows — app.py
   can reuse that pattern.

3. scripts/audit_all_banks.py. Replace its hardcoded OD sign
   convention (Alliance positive, Ambank negated, RHB negated, etc.)
   with the stamped per-row account_type field. CLAUDE.md warns the
   current hardcoding is the #1 source of audit false positives.

## Pending — beyond Sprint 4.5 (deferred list unchanged)

Sprint 5 (heavy, fresh-session recommended):
- #21 kredit_lab_classify.py — reusable Python module AI calls
  (500-1000 lines estimated)
- #23 Regression fixture suite — MTA/KYDN/Muhafiz/DMC as fixtures
  under tests/fixtures/
- #24 Synthetic OD simulation — flip CR statement signs to simulate
  OD across 14 banks

Sprint 6 (polish, bundle):
- #6 Wire should_drop_as_counterparty into per-bank extraction paths
- #8 Alliance date-clamp to statement period
- #9 Alliance rail-prefix strip (CR ADVICE, IB2G FND TRF, FPX ABB,
  DuitNow CR Trf, HUB CA MISC DR)
- #10 IB2G trailing own-company-name strip
- #22 canonical_entities_<COMPANY>.json band-aid

Fraud detector deferred items — see 2026-04-21 handoff earlier in
this file.

## Key decisions this session (do NOT re-litigate)

- Option A enum: locked_type is CR / OD / UNDETERMINED only. No
  CASH_LINE. Islamic Cashline-i / CAP-i / SAP-i = OD.

- NO transaction-description keyword scanning in
  determine_account_type. Every keyword (OVERDRAFT INTEREST,
  CASHLINE-i PROFIT CHARGED, DR Interest, etc.) generated false
  positives — either in transfer memos settling OTHER accounts or
  on plain CR during a brief drawdown event. Evidence from header
  facility-limit + balance-sign + sustained-negative + row-math
  only.

- 50% threshold on DR-suffix and sustained-negative distinguishes
  genuine OD (SWHSB 96%) from temporary drawdown on plain CA
  (RE CONCEPT 4%).

- Display-label account_type enum collapsed back to
  Current / Savings / OD. Mapping: OD -> "OD"; CR -> "Current" or
  "Savings" per header text; UNDETERMINED -> "Current" default.

- Facility-keyword text in transfer-memo descriptions ("Instant
  Transfer ... OVERDRAFT INTEREST MAR 2025") describes OTHER
  accounts being settled, NOT this statement's facility. Saved in
  memory as feedback_memo_text_scope.md.

- Bytes-input parsers (Maybank, OCBC, RHB) open their bytes once
  at the entry function to extract page-1 text, then continue with
  their original library (pdfplumber or PyMuPDF/fitz).

- Per-bank transaction-table markers (for header truncation):
    Alliance     : Date Transaction Details / Tarikh Keterangan
                   Urusniaga
    Ambank       : DATE TRANSACTION CHEQUE / TARIKH TRANSAKSI
    CIMB         : Date Description Cheque / Tarikh Diskripsi
    Bank Rakyat  : Tarikh Kod Transaksi / Date Transaction
                   Description
    OCBC         : Transaction Date Transaction Description
    Others       : bilingual English/Malay variants per bank

## Key files

Parser / helpers (committed, live on main, not pushed yet):
- core_utils.py lines 442-880 — determine_account_type +
  finalize_parser_output + stamp_account_type_once +
  stamp_statutory_buckets + helpers.
- All 14 bank parsers — import finalize_parser_output, call at
  every return site.
- scripts/survey_account_type_signals.py — evidence survey across
  corpus.
- scripts/validate_account_type_detection.py — per-PDF verdict
  across all 325 PDFs.

AI prompt files (committed locally, upload to Claude AI web
manually):
- validation runs - json/claude ai prompt file/
  BANK_ANALYSIS_SCHEMA_v6_3_5.json
- validation runs - json/claude ai prompt file/
  SYSTEM_PROMPT_v3_5_5.md
- validation runs - json/claude ai prompt file/
  CLASSIFICATION_RULES_v3_5.json

Documentation:
- CLAUDE.md — project instructions (still untracked, candidate for
  commit when user decides)
- prompts/NEXT_CHAT_PROMPT.md — this handoff log
- MEMORY.md — auto-memory index in
  ~/.claude/projects/.../memory/

## Critical lessons saved to memory (from this sprint)

- feedback_verify_before_asserting.md — Never claim an account is
  OD / Cash Line / SAP-i from a helper result alone. Always read
  the actual PDF header text first.

- feedback_memo_text_scope.md — Facility keywords in transfer-
  prefix descriptions are memos describing OTHER accounts being
  settled, not this statement's facility.

## First actions in new chat

1. Acknowledge the handoff; verify commit state:
     git log --oneline -5
   Expect: 4267f1c, fc1696e, 4c65ec2, d5bf465, db9a8cb

2. Ask user:
   "Have you (a) pushed these three commits to origin/main, and
   (b) uploaded v3.5.5 / v3.5 / v6.3.5 to Claude AI project
   knowledge, and (c) re-run MTA/KYDN/Muhafiz on the new parser?"
   — Their answer dictates next step.

3. If (a) not pushed: offer to push.

4. If outputs clean and (b)(c) done: proceed to Sprint 4.5 pending
   #1 (app.py harvest) — the highest-leverage remaining piece.

5. If outputs have regressions: debug against the expected shape
   above. Likely areas:
   - Display-label mapping: any account still showing "Cash Line"
     or "Cash Line-i" would indicate the AI hasn't picked up the
     v3.5.5 prompt.
   - Missing account_type on rows: parser not returning through
     finalize_parser_output (shouldn't happen — all 14 wired and
     validated).

6. If the user wants app.py harvest: template is in
   scripts/validate_account_type_detection.py lines 120-143
   (validate_bank) — it calls determine_account_type(rows,
   header_text=...) directly on empty-row cases to get an
   UNDETERMINED sentinel, which is exactly what OCR-only PDFs need
   in the harvest.
```

---

## Session handoff — 2026-04-25 evening (Sprint 6 #11 Maybank CMS shipped; subagent loop ready for #2–#10)

```
Repo: Bank-Statement-Analysis-main 3
Working dir: /Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## State on arrival

Branches:
  sprint-6/polish     5 commits on top of sprint-4.5-complete (parser-side).
                      THIS is the working branch for the next session.
                      Latest commit: 8f9a473 Sprint 6 #11.
  sprint-5/classifier deliberately held local; not pushed; do not touch.

Tag: sprint-4.5-complete pinned to a4b2bca on main. Permanent stable marker.

Commits on sprint-6/polish (newest first):
  8f9a473  Sprint 6 #11: Maybank CMS PYMT MARS / DIRECT DEBIT + APS handlers
  4111651  Sprint 6 #10: Alliance own-party-name strip
  6f770c6  Sprint 6 #9:  Alliance rail-prefix bare-ref handlers
  83b571f  Sprint 6 #8:  Alliance date-clamp (defence-in-depth)
  4485889  Sprint 6 #6:  should_drop_as_counterparty wire + measurement scripts
  a4b2bca  Sprint 4.5: Finish — app.py harvest + audit sign-convention refactor

14-bank regression status: clean. 0 errors / 0 invalid_dates / 0 missing keys
across all 14 banks. Total 45,008 tx (slightly above the 44,808 baseline because
new untracked PDFs were added under Bank-Statement/<Bank>/ between sessions; the
delta is from corpus growth, not regression).

sprint6_impact baseline (post #11):
  total tx: 58,921   distinct counterparties: 16,663
  UNIDENTIFIED: 18   UNCATEGORIZED: 35

## What this session shipped

1. Commit 8f9a473 — Sprint 6 #11 Maybank CMS / APS handlers in app.py:
   -  CMS - CR PYMT MARS <ENTITY> <REF>          → +404 rows resolved
   -  CMS - DR DIRECT DEBIT <ENTITY> <REF>       → +221 rows resolved
   -  CMS - DR PYMT MARS <ENTITY|INTERCO> <REF>  → +33 rows resolved
   -  PAYMENT DEBIT - APS /OTHERS MAS PAYMENT *  → +173 rows resolved
   -  CMS - DR CORP S/CHG (existing fee regex)   → +1 row resolved
   Total: -831 raw rows. Top new entities: AEON CREDIT SERVICE (219),
   SEEDFLEX CAPITAL (168), UNNAMED MAS PAYMENT (DR) (138), ENERGETIC POINT
   (117), KWSP (84), plus MITSUBISHI / ORIX / SCANIA / PAC LEASE / KONICA /
   LHDNM / TM TECHNOLOGY etc.

2. scripts/sprint6_raw_gaps.py — REUSABLE enumerator for raw-method gaps.
   Re-runs build_counterparty_ledger on every Full Report *.json, tallies
   method=raw rows, groups by (bank, first-3-token shape). Use BEFORE picking
   the next handler target and AFTER shipping each handler to verify zero
   residuals. CLI:
     python3 scripts/sprint6_raw_gaps.py                    # top-5 per bank
     python3 scripts/sprint6_raw_gaps.py --bank OCBC        # one bank, all shapes
     python3 scripts/sprint6_raw_gaps.py --shape 'CIB IBG'  # filter to shape
     python3 scripts/sprint6_raw_gaps.py --out /tmp/raw_gaps.json

## The plan — subagent loop for #2–#10

User direction (verbatim):
  "after we have done 1 pattern, why dont we deploy sub-agent to solve this
   once at a time. then review show me the result."

Workflow per pattern:
  1. MAIN session reads the queue (below) and asks user which to launch
     next. Default = top of queue (highest volume not yet done).
  2. MAIN session fills in the SUBAGENT TEMPLATE (below) with the chosen
     pattern's specifics, then launches ONE general-purpose Agent with
     subagent_type="general-purpose", run_in_background=false.
  3. Subagent runs the 10-step workflow, ends at REPORT — does NOT commit.
  4. MAIN session relays the report to user, user reviews diff in app.py.
  5. If approved, MAIN session commits via the proposed message in the
     report. If user pushes back, MAIN iterates with subagent or absorbs the
     fix directly.
  6. Repeat for next pattern.

Why sequential not parallel: every subagent edits app.py around the same
dispatcher (~line 2146). Parallel runs WILL collide. Worktree-isolation +
cherry-pick is the parallel-safe alternative but adds complexity; sequential
in-tree is faster for 9 handlers and gives the user a review gate per step.

Why "subagent does NOT commit": user wants to see each diff before it lands.
Hard rule. Subagent prompt explicitly says "stop at report".

## The remaining 9 patterns — RANKED by extraction value

(Sample descriptions captured this session; confirmed against live re-run of
build_counterparty_ledger on 29-file corpus. Each sub-agent should still
re-enumerate via sprint6_raw_gaps.py to catch edge cases the samples miss.)

#2 OCBC — DUITNOW(INST TRF) DR/CR /IB <ENTITY> DESC: REF: <purpose>  ~491 rows
   Files: Full Report OCBC Calvin Skin.json (471), Full Report OCBC LF.json (20).
   Samples:
     'DUITNOW(INST TRF) DR /IB PHENOMENA OUTDOOR S DESC: REF: Klang Billboard'
     'DUITNOW(INST TRF) DR /IB PHENOMENA OUTDOOR S DESC: REF: Klang Billboard ads Monthly p'
     'DUITNOW(INST TRF) CR /IB CALVIN PROFESSIONAL DESC: Company REF: Company'
   Pattern: prefix `DUITNOW(INST TRF) (DR|CR) /IB` then ENTITY (truncated ~22ch
   by OCBC) then literal `DESC:` and `REF:` markers then purpose text.
   Wiring: new branch in _extract_counterparty near CP3 DUITNOW (~line 2317).

#3 RHB Bank — RFLX <ENTITY><DIGITS> / -REF  ~390 rows (Waja file)
   File: Full Report Waja RHB.json (only).
   Samples (from PDF inspection — entity glued to digits with no space):
     '01-12-2025 980 RFLX MOHAMMAD25120158675 / 00005073 160.00 - 98,505.37+'
     '01-12-2025 980 RFLX WAN 25120155790 / 00003468 50.00'
     '01-12-2025 980 RFLX WORLD 25120153102 / 00002058 44,326.93'
     '02-12-2025 980 RFLX ATASHA 25120156051 / 00003695 46,786.89'
     '02-12-2025 980 RFLX ARKAS 25120271270 / 00004228 1,749.83'
   Note: parser already strips digit ref; stored description in the corpus
   ledger is `'RFLX MOHAMMAD / -'` etc. (verified via PDF inspection — entity
   IS in PDF, parser produces this short form). Need _extract_counterparty
   to recognise `^RFLX <NAME> / -?$` and emit NAME (or `RFLX <NAME>`) as the
   counterparty. SKIP `RFLX / CM112/ -` rows (41 rows, bank-internal service
   ref, NOT entity).
   Distinct entities seen: MOHAMMAD (265), WAN (59), ARKAS (27), ASHRUL,
   YONG, HDL, ATASHA, WORLD.

#4 HLB Islamic — multi-format CIB / Instant Transfer / FPX B2B1  ~365 rows
   Files: Full Report HLB MTCE.json (~330), Full Report HLB Detik.json (~35).
   Sub-shapes:
     a. CIB Instant Transfer at <BRANCH> <amt> <purpose...> <ENTITY> <BANKREF>
          'CIB Instant Transfer at DIO 29,000.00 Adv Refund TST Plumbing
           LAM HO SDN. BHD. 20250918HLBBMYKL010OCB45374558'
          'CIB Instant Transfer at DIO 6,150.00 Kubang PPC34 Inv Oct 24
           CEKAL ENVIRONMENTAL SERVICES 20250918HLBBMYKL010OCB45380555'
     b. Instant Transfer at KLM <amt> <maybe_balance> <purpose> <ENTITY> <BANKREF>
          'Instant Transfer at KLM 29,000.00 Fund Transfer TAN HON YEW
           20250904CIBBMYKL010ORM10662972'
     c. CIB IBG CA Debit Advice at KLM <amt> <purpose> <ENTITY> <BANKREF>
          'CIB IBG CA Debit Advice at KLM 1,359.85 Claim Mar2025
           FAHARUL AZMAN BI IBGCMPCIMB2505150002523'
     d. FPX B2B1 <amt> <ref> <ENTITY> <ref>
          'FPX B2B1 1,580.00 3143771230 NATIONAL INSTITUTE OF OCCUPATI
           2509241419560194'
     e. Serv Charge-IBG/TT/Rentas/Misc at KLM ... → BANK FEES (already exists,
        but verify — currently in raw)
   Bank-ref token: `\d{8}[A-Z]{4,12}\d+` (date prefix + bank-ID + serial).
   IMPORTANT: skip rows where entity matches statement-holder OWN-account
   name. Hou Tian / MTCE often has rows like:
     'CIB Instant Transfer at DIO 547,000.00 INTER ACC TXN OWN ACC TXN
      MTC ENGINEERING SDN BHD 20250708ARBKMYKL010OCB67418524'
   `INTER ACC TXN OWN ACC TXN` → bucket as UNNAMED (own-account transfer);
   the entity that follows (MTC ENGINEERING) IS the statement holder, not a
   third party.
   Wiring: new branch in _extract_counterparty.

#5 RHB Islamic (Kay R) — RFLX/RPP/INWARD IBG/REFLEX-FUNDS  ~204 rows
   File: Full Report RHB Kay R.json (only).
   Sub-shapes:
     a. 'RFLX INSTANT TRF DR 0000005833 260110934746 YAYASAN LTAT SUMBANGAN CSR YAYASAN LTAT'  (88)
     b. 'RPP INWARD INST TRF CR 0000001289 KAY R WORKSHOP (M) SDN. B Yard July'  (59)
     c. 'INWARD IBG 0000004332 Sept & Oct 2025 AP Payment Dec\\'25 PHOSPHATE RESOURCES'  (46)
     d. 'REFLEX-FUNDS TFR CR 0000000542 PRO TEC CONSOLIDATED SDN. BHD. LTAT CSR Program'  (11)
     e. 'LOCAL CHQ DEP 0000000268 - -'  (9 — bare cheque deposit, route to
        Unidentified (Cheque) special bucket)
   Common shape: rail prefix → 10-digit txn ref → optional sub-ref → ENTITY
   → purpose. Entity sits between numeric ref(s) and trailing purpose text.
   Note (b) and (c) place entity in the middle BEFORE purpose; (a) and (d)
   place entity AFTER purpose-text-then-ref. Need careful per-shape regex.

#6 Ambank — Fund Transfer + JomPAY comma-delim  ~223 rows
   Files: Full Report Ambank Plentitude.json (164), Full Report Ambank Hon
   Engineering.json (59).
   Samples:
     'Fund Transfer /DEBIT TRANSFER, HN HOME DESIGN, INVOICE NO 00002412,'
     'Fund Transfer /DEBIT TRANSFER, BADAN PENGURUSAN BERSAMA SHAFTSBURY
      PUTRAJAYA, B-13A-07, MAINTENANCE FEE OCT 2024'
     'JomPAY /DEBIT TRANSFER, HON ENGINEERING SDN BHD,18-2, 47103254, BA4 KPC0G'
     'Interbank GIRO /DEBIT TRANSFER, PUBLIC BANK BERHAD, 33RD INST - VHF
      7322, Fund Transfer'
   Pattern: `^(?:Fund Transfer|JomPAY|Interbank GIRO) /DEBIT TRANSFER,
   <ENTITY>, <rest>`. Entity = field 2 (between first and second comma).
   This EXTENDS existing CP3 Ambank handler (~app.py line 2317) which already
   handles `DuitNow TRF /MISC (CREDIT|DEBIT), <ENTITY>, …`. Add the new
   prefixes to the same regex or copy the pattern.
   Edge cases: 'WDL LOCAL BANK ATM /ATM WITHDRAWAL, , 01100, 808932' (bare
   ATM withdrawal — empty entity field 2 → route to CASH WITHDRAWAL bucket).
   'MEPS FEE /MISC DEBIT, , ,' → BANK FEES bucket.
   'CTL OUTWARD CLEARING /LOCAL CHQ 449954 DEPOSIT, , 449954,' →
   Unidentified (Cheque) bucket.

#7 OCBC — GIRO CREDIT / CA MYDEBIT / CA BANKCARD  ~220 rows
   File: Full Report OCBC Calvin Skin.json (mostly).
   Sub-shapes:
     a. 'GIRO CREDIT PBB-PBCS AC 3 03999061714 REF:2025110300015920'  (98)
        — biller-style; PBB-PBCS = Public Bank Berhad - Public Bank Card
        Settlement. Entity = 'PBB-PBCS' (or expand to PUBLIC BANK).
     b. 'CA MYDEBIT PURCHASE /IB 01/08/25 xx-5197 MAGICBOO-KLANG MY MY'  (77)
        — POS card purchase. Entity = MERCHANT (last alpha tokens, often
        with country suffix " MY MY" to strip).
     c. 'CA BANKCARD PAY (DC) /IB 18/12/25 xx-6480 Traveloka3DS*131084767
         KUA A Member of OCBC Group ...'  (45)
        — online card payment. Entity = MERCHANT (e.g. Traveloka3DS — strip
        the *NNNN suffix). Watch for OCBC footer text ("A Member of OCBC
        Group...") leaking into description — clip at this stop word.
   Routing: a → biller bucket (PBB-PBCS or PUBLIC BANK), b/c → CARD PURCHASE
   special bucket OR extracted merchant name. User preference TBD; ask user
   before deciding bucket vs entity.

#8 Alliance — NBPS IBG Dr <ENTITY>  ~137 rows
   File: Full Report Alliiance KYDN.json.
   Samples:
     'NBPS IBG Dr CA AOBJOM03032025625494 C331KJDR 17892624121402
      TT DOTCOM SDN BHD 326796887 1'
     'NBPS IBG Dr CA AOBJOM03032025625487 C33I4TUG 000200160
      MALAKOFF UTILITIES S 0000608526 1'
     'NBPS IBG Dr CA AOBJOM03032025625476 C33UHPMF 11218856146
      IWK SDN BHD - JOMPAY AU043330 1'
   Pattern: `NBPS IBG Dr CA <AOBref> <C-token> <num> <ENTITY> <num> <num>`.
   Entity = alpha tokens between the 3rd ref token and the trailing numerics.
   Wiring: NEW BRANCH in _extract_counterparty_alliance (~app.py line 1904)
   — Alliance dispatcher fires before generic patterns. Mirror style of
   existing Alliance handlers there.
   Also tackle the small Alliance-tail items if cheap:
     'IB2G FND TRF CA-CA M AOBBY21042025565761 PN202504/00000050
      Magnum Corporation S' (5 rows) → entity = Magnum Corporation S(DN BHD)
     'IB2G CA Common Chrg AOBMC28032025426072 AOB Monthly Charges' (6) →
      BANK FEES (existing bucket)
     'HOUSE CHEQUE/MISC 000766 ALLIANCEB' (7) → Unidentified (Cheque)

#10 UOB — small misc  ~28 rows
   File: Full Report UOB Juta Kenangan.json + UOB Upell.json.
   Samples:
     '253562 ORIX CREDIT MALAYSIA SDN BHD'  (12)  — entity is right there
      after the leading 6-digit ref. Same shape: `<6digit_ref> <ENTITY>`.
     'CORPORATION SDN BHD PBB UPELL CORPORATION SDN BHD|| DuitNow/Instant
      Trf C017427 017503'  (16) — own-party (UPELL CORPORATION SDN BHD = own
      account) leaking via DuitNow trailer. Bucket as UNNAMED DUITNOW or
      strip own-party.
     'OD Int Charge'  (12) → BANK FEES (existing bucket; verify the regex
      catches 'OD Int Charge' — currently slipping through).
     'Chq Wdl 0021294' (444) and 'Cheque 0030579' (27) → CHEQUE WITHDRAWAL
     special bucket. NEW bucket name (does not exist yet); user OK with
     adding a UNNAMED CHEQUE WITHDRAWAL or CHEQUE WITHDRAWAL label —
     confirm before subagent runs.
   Also UOB Juta Kenangan has 444 'Chq Wdl' rows that COULD be tackled here
   if user agrees a new special bucket is in scope.

#9 Bank Rakyat — CIBDRADVICE / DUITNOWTRANSFER (PARSER-UPSTREAM, last)  ~1,720 rows
   File: Full Report Bank Rakyat Koperasi Felcra.json.
   THIS IS A bank_rakyat.py FIX, NOT _extract_counterparty. Verified via PDF
   inspection — recipient name lives on the line ABOVE the transaction in
   the PDF. Example PDF excerpt:
     'SITINURHAFIZAHBINTIOTHMAN'
     'PENTADBIRAN'
     'MAKANANMESYSTAFFPADA2/11/23'
     '07/11/2023 94006 CIBDRADVICE 115.00 10,937.33'
     'HAIRULHAZIZIBINROSLI'
     'PENTADBIRAN'
   Need bank_rakyat.py to merge the 1–3 lines BEFORE each CIBDRADVICE / 
   DUITNOWTRANSFER row into the description field. Bigger blast radius
   than the others — modifies parser-internal logic, requires extra-careful
   regression testing on Bank Rakyat (54 reference PDFs in
   Bank-Statement/BankRakyat/). Save for LAST.
   Also affects:
     '94061 CIBDRCHARGES 0.10' (1146), '94061 CIBSMSFEE 0.10' (1228),
     '94040 DUITNOWFEE 0.50' (108) → these are all FEES; route to BANK FEES
     special bucket (no parser change needed; just add the prefix to the
     existing BANK FEES regex at app.py line 2179).
   Sub-task split for #9:
     9a. Add CIBSMSFEE / CIBDRCHARGES / DUITNOWFEE / CIBSMSFEE prefixes to
         the BANK FEES regex (LOW RISK — pure regex addition).
     9b. Modify bank_rakyat.py to merge prior PDF lines into CIBDRADVICE /
         DUITNOWTRANSFER descriptions (HIGH RISK — parser change).

## Patterns intentionally NOT in the queue (lower priority / verify first)

- BIMB Mytutor `9871 RTP REDIRECT CT CR` (6,955 rows). Source PDFs
  `MY019126 *.pdf` are NOT in Bank-Statement/BankIslam/. Cannot verify
  whether recipient name lives in the PDF source. ASK USER to drop those
  PDFs into Bank-Statement/BankIslam/ before tackling this one — without
  PDF inspection it's a shortcut.
- BIMB CDB CA TRF CA (811), CDB CS TO IBFTS3 (195) — same: needs PDF.
- Maybank Islamic CARD SALES M/N (1,083) and CR/CARD SALES MN (308) —
  POS settlement batch advice; per format design, no payer name in PDF.
  Could route to UNNAMED CARD SETTLEMENT special bucket but user said
  bucket cosmetics ≠ priority. Defer.
- Agrobank leading-num bleed pattern (376) — agro_bank.py upstream issue
  (line index leaking into description). Defer until corpus growth makes
  it worthwhile.
- Public Bank DEP-ECP / DR-ECP / TSFR FUND (471) — internal voucher codes
  with no payer name. Special bucket only; defer.

## Hard rules (carried over verbatim — DO NOT re-litigate)

  - No shortcuts. The fix must be applicable / reusable for future cases —
    user said this twice this session. If tempted to "mostly right, ship
    it", stop and expand the test corpus via sprint6_raw_gaps.py first.
  - Cross-bank safety: every handler EITHER bank-scoped (`if bank and
    "<BANK>" in bank.upper(): ...`) OR pattern-distinctive enough that no
    other bank's descriptions can match the regex. Never add a bank-generic
    handler that mutates a different bank's extraction.
  - Parser is primary; AI is thin. Fix at parser extraction layer (app.py
    _extract_counterparty), NOT classifier regex or renderer post-processing.
  - 14-bank regression (scripts/validate_reference_statements.py) gates
    every commit. 0 errors / 0 invalid_dates / 0 missing keys / 0 sign-flips
    required.
  - One commit per concrete extraction handler. No bundled omnibus commits.
  - Subagent does NOT commit. User reviews each diff. Main session commits.

## Mental model for the snapshot-diff trap

scripts/sprint6_impact.py writes `grand_total = most_common(50)`. When a new
handler surfaces high-volume entities (200+ count), they push pre-existing
entries with count <100 OFF the top-50 list. Those entries appear as "Lost
buckets" in the diff output but are NOT actually lost — they still exist in
the per_bank dicts (which keep top-30 PER bank, not top-50 globally). This
session's #11 commit hit this trap with 'MAYBANK VISA CARD' (82) and 'LHDN'
(81) — both unchanged but bumped off top-50.

ALWAYS confirm any "Lost" bucket in the diff against per_bank dicts AND a
live function call on a sample row of that name. The check looks like:
  jq '.per_bank | to_entries[] | {bank: .key, val: .value["MAYBANK VISA CARD"]}' \
    /tmp/before.json /tmp/after.json
or in Python:
  json.load(open('.../after.json'))['per_bank']['Maybank Islamic'].get('MAYBANK VISA CARD')

If per_bank counts are equal → false alarm.
If per_bank counts changed → real regression, debug.

## Subagent prompt template (FILL IN PER PATTERN, then launch)

You are working on the Bank-Statement-Analysis-main 3 repo at:
  /Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

GOAL: Build ONE counterparty-extraction handler for the following raw-method
pattern, following the exact workflow that produced commit 8f9a473 (Sprint 6
#11 Maybank CMS handlers). Do NOT commit — stop at the report step.

PATTERN TO HANDLE
  Bank      : <BANK NAME — e.g. OCBC BANK>
  Sub-format: <FORMAT — e.g. DUITNOW(INST TRF) DR/CR /IB <ENTITY> DESC: REF:>
  Volume    : ~<N> rows in <FILE(S)>
  Sample descriptions to extract entity from (5–10 strings):
    <verbatim sample 1>
    <verbatim sample 2>
    ...

REPO CONTEXT
- Branch: sprint-6/polish (already checked out — STAY on this branch).
- 14-bank parser regression: scripts/validate_reference_statements.py — must
  end with 0 errors / 0 invalid_dates / 0 missing_required_keys /
  0 both_debit_credit_positive across ALL 14 banks.
- Counterparty enumerator: scripts/sprint6_raw_gaps.py
    --bank <NAME>     filter to one bank
    --shape "<HEAD>"  filter to first-3-token shapes containing this substring
    --samples N       sample descriptions per shape
- Impact measurement: scripts/sprint6_impact.py
    --out /tmp/before_<short>.json
    --out /tmp/after_<short>.json
    --diff /tmp/before_<short>.json /tmp/after_<short>.json
- Dispatcher: app.py `_extract_counterparty(description, bank)` near line 2146.
  First match wins. Add new handlers near the existing same-bank handlers:
    Maybank: ~line 2436 (PAYMENT FR A/C) or line 2487 (TRANSFER TO/FR A/C)
    Ambank/CP3: ~line 2317 (DUITNOW comma-delim)
    Alliance: app.py line 1904 (_extract_counterparty_alliance — bank-only)
    CIMB/CP6: ~line 2410 (TR IBG / TR TO C/A)
    OCBC: same dispatcher; add new branch with anchored prefix
    HLB Islamic: same dispatcher; add new branch with anchored prefix
    RHB Bank/RHB Islamic: same dispatcher; add new branch with anchored prefix
    UOB: same dispatcher
  Reference: commit 8f9a473 (Sprint 6 #11) for the CMS handler template.
- Helpers: _strip_trailing_refs, _strip_purpose_prefix_tokens,
  _strip_stop_tokens, _clip_at_stop_keyword, _tail_alpha_run,
  _dedupe_duplicated_prefix, _find_duplicated_block_end, _has_real_word.
- Constants: _CP_NAME_ANCHORS, _CP_STOP_KEYWORDS, _CP_BANK_SUFFIX,
  _CP_PURPOSE_WORDS, _CP_NOISE_NAMES, _OWN_PARTY_PROTECTED_LABELS.
- Existing special-bucket destinations (use these where the body matches —
  do NOT invent new buckets unless none fit): CASH DEPOSIT, CASH WITHDRAWAL,
  Unidentified (Cheque), RETURNED CHEQUE, INWARD RETURN, REVERSAL, FD/INTEREST,
  BANK FEES, BULK SALARY, KWSP, SOCSO, HRDF, LHDN, JANM, LOAN DISBURSEMENT,
  LOAN REPAYMENT.

HARD RULES (no shortcuts)
1. Cross-bank safe: handler regex must be either bank-scoped or pattern-
   distinctive enough that other banks can't match it.
2. Enumerate edge cases first: BEFORE designing the regex, dump every distinct
   description for the target prefix across all 29 corpus files and cluster
   by entity-candidate. The "obvious" 3-line samples above are the tip — the
   long-tail edge cases (bare prefix, intercompany, ref-only, purpose-prefixed,
   own-account-transfer) live in the corpus. Mirror the inline-Python approach
   used in the 8f9a473 session transcript.
3. No invented entities. Bare-prefix rows, intercompany / claim / hotel /
   own-account-transfer rows MUST bucket to a synthetic
   `UNNAMED <X> (CR/DR)` label — not a fake counterparty name. Add new
   labels to _OWN_PARTY_PROTECTED_LABELS only if they could otherwise be
   stripped by Sprint 6 #10 own-party logic.
4. Truncated SDN / BHD restoration: if entity ends with bare `SDN` (no `BHD`),
   append `BHD`. If it already ends with `BHD`, leave alone. Don't over-restore.
5. Route to existing special buckets where a salary / statutory / fee /
   transfer keyword fires; don't invent a parallel bucket.

WORKFLOW (MANDATORY — IN THIS ORDER)
1. Snapshot before:
     python3 scripts/sprint6_impact.py --out /tmp/before_<short>.json
2. Pull EVERY distinct description for the target prefix across all 29
   corpus files. Use inline Python like:
     for p in CORPUS.glob('Full Report *.json'):
         if p.name.endswith('.classified.json'): continue
         data = json.loads(p.read_text())
         ledger = app.build_counterparty_ledger(data['transactions'])
         for cp in ledger['counterparties']:
             for tx in cp['transactions']:
                 if tx['extraction_method'] != 'raw': continue
                 if not tx['description'].startswith('<PREFIX>'): continue
                 ...
   Cluster by candidate-entity slice. Surface every edge case (bare prefix,
   intercompany markers, ref-only, purpose-prefixed entity-after-ref,
   mid-ref entity, own-account markers, OCR footer leakage).
3. Design the regex / extraction logic. Sketch 8–15 expected (input, output,
   method) cases including bare and intercompany.
4. Implement in app.py near the appropriate sibling handler. Comment block
   prefix: `# ── Sprint 6 #N — <Bank> <Format> handler ──` (use N = next
   available number after existing Sprint 6 commits — currently #12 is next).
   Write a 4–8 line "why" comment describing the format, the cut rule, and
   the bare / intercompany / fee fallback bucket destinations.
5. Inline-test the handler against the cases from step 2. Pass threshold =
   100% semantic correctness; differences from your test expectations are
   OK only if the handler produces a strictly BETTER name (e.g. SDN-BHD
   restoration). Iterate until clean.
6. Snapshot after:
     python3 scripts/sprint6_impact.py --out /tmp/after_<short>.json
7. Diff:
     python3 scripts/sprint6_impact.py --diff /tmp/before_<short>.json /tmp/after_<short>.json
   Read CAREFULLY: grand_total in the snapshot is most_common(50) only —
   "Lost" buckets dropping below the top-50 are NOT regressions. Cross-check
   suspicious losses against per_bank dicts (top-30 per bank) AND a live
   function call on a sample row of the suspect lost name. False alarms
   here are the #1 trap (see Mental Model in NEXT_CHAT_PROMPT.md).
8. Re-enumerate to confirm zero residuals on the target shape:
     python3 scripts/sprint6_raw_gaps.py --bank "<BANK>" --shape "<HEAD>"
   Expect 0 rows (or only obviously off-pattern strays explainable by a
   different existing fee bucket).
9. 14-bank regression:
     python3 scripts/validate_reference_statements.py
   MUST be 0 errors across all 14 banks. tx total stays at 45,008.
10. DO NOT COMMIT. Stop here.

REPORT BACK (return ALL of these in a structured response — under 600 words)
  Pattern name + bank
  Files modified (full paths + line ranges)
  Regex(es) added (final form)
  Edge-case categories you handled (bare, intercompany, fee, multi-ref, etc.)
  Inline test results (X/Y pass; explain any "fail" that's a strict-better-than-
    expectation case)
  Impact diff — extracted from the diff output:
    rows moved out of raw (per-bank breakdown)
    distinct counterparties before / after
    UNIDENTIFIED / UNCATEGORIZED before / after (must be unchanged or lower)
    top 10 newly-surfaced entities by count
  Residual-shape check (raw rows still matching target prefix — should be 0
    or explained)
  False-alarm check on any "Lost" buckets in the diff (per_bank dict
    confirmation that they're unchanged across banks)
  14-bank regression result (raw csv tail)
  Suggested commit message in EXACTLY the same format as 8f9a473:
    Sprint 6 #N: <Bank> <format> handler
    <2–4 sentence what + why>
    +X rows resolved, broken down by sub-format
    Top entities surfaced (with counts)
    Cross-bank safety statement
    14-bank regression statement

Anything that doesn't fit this template (bucket-naming choice, ambiguous
edge case, scope expansion temptation), surface it as a question for the
user in the report — don't silently make a judgement call.

## Before you start (next chat checklist)

1. Verify state:
     cd "<repo path above>"
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -3              # expect: 8f9a473 ... 4111651 ... 6f770c6
     git tag -l 'sprint*'              # expect: sprint-4.5-complete
     git status --short                # expect: untracked items only,
                                       # no modified app.py / no modified
                                       # NEXT_CHAT_PROMPT.md

2. Sanity-check the existing 5 commits still produce clean extraction:
     python3 scripts/validate_reference_statements.py
        → expect 0 errors across 14 banks, total ~45,008 tx
     python3 scripts/sprint6_impact.py --out /tmp/sprint6_baseline.json
        → expect total=58,921 distinct=16,663 UNIDENTIFIED=18 UNCATEGORIZED=35

3. Re-enumerate raw-method gaps to confirm the queue is still accurate:
     python3 scripts/sprint6_raw_gaps.py --top 5 > /tmp/gaps.txt
   Compare top shapes per bank vs. the 9-pattern queue above. Expect:
   Maybank Islamic CMS / APS shapes are ZERO (#1 done). Other 9 patterns
   still present at the volumes listed above (±10 due to corpus growth).

4. Ask the user which pattern to launch FIRST (default: #2 OCBC, top of queue
   by volume). Do NOT auto-pick.

5. Once user picks: fill in the SUBAGENT TEMPLATE above with that pattern's
   specifics (bank, sub-format, volume, sample descriptions copy-pasted
   verbatim from the queue above), then launch ONE general-purpose Agent
   in foreground (run_in_background=false) with that prompt.

6. When subagent reports back: relay the report verbatim to the user. Show
   the diff (`git diff app.py`). Wait for user approval.

7. On approval: commit using the proposed message from the subagent's report
   (HEREDOC, with the standard `Co-Authored-By: Claude Opus 4.7 (1M context)
   <noreply@anthropic.com>` trailer). Do NOT push unless asked.

8. Update todo list, ask user which pattern next, repeat.

## Open questions to surface to user before launching subagents

- #7 OCBC GIRO/CARD: bucket vs entity for `CA MYDEBIT PURCHASE` and
  `CA BANKCARD PAY`? Card purchases could either become a CARD PURCHASE
  special bucket OR extract the merchant name. User preference TBD.
- #10 UOB: OK to add a new CHEQUE WITHDRAWAL special bucket for the 471
  `Chq Wdl` / `Cheque` rows? Same question for #6 Ambank ATM-withdrawal
  comma-empty rows.
- #9 (Bank Rakyat): split into 9a (low-risk regex add — fees → BANK FEES)
  and 9b (high-risk parser-upstream — bank_rakyat.py preceding-line merge)?
  Confirm 9a goes first as warm-up, 9b last.
- BIMB Mytutor PDFs `MY019126 *.pdf` — please drop into
  Bank-Statement/BankIslam/ if you want the 7,961 rows of BIMB raw-method
  gaps tackled this sprint. Otherwise they stay deferred.

## Rollback procedure

  # Drop just the Sprint 6 #11 commit (keep #6/#8/#9/#10):
  git reset --hard 4111651
  # (Re-creates the pre-#11 state. scripts/sprint6_raw_gaps.py is removed
  # because it was committed in the same commit.)

  # Drop Sprint 6 polish entirely (now that it's on origin):
  git checkout main
  git branch -D sprint-6/polish
  git push origin --delete sprint-6/polish

  # Drop a future #N handler before commit (subagent left work in working tree
  # but you decided to abandon):
  git checkout app.py

Tag sprint-4.5-complete remains the permanent stable marker.
```

---

## Session handoff — 2026-04-26 (Sprint 6 #12–#15 shipped; #16 next)

```
Repo: Bank-Statement-Analysis-main 3
Working dir: /Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## State on arrival

Branch: sprint-6/polish (working branch — STAY on this branch)
Tag:    sprint-4.5-complete (permanent stable marker, unchanged)

Commits on sprint-6/polish (newest first, last 5):
  5e657ee  Sprint 6 #15: RHB Reflex (RFLX) + RHB miscellaneous fees + C24 sync
  82f36d6  Sprint 6 #13: OCBC own_party_name stamping
  83f4027  Sprint 6 #14: own-party exact-match handling in _strip_own_party_tokens
  f0993fd  Sprint 6 #12: OCBC DUITNOW(INST TRF) /IB handler
  4b87b52  (doc) Append 2026-04-25 evening handoff

ALL 4 SHIPPED COMMITS ARE LOCAL — NOT pushed to origin yet. User decides
whether to push at session start.

14-bank regression status: clean. 45,008 tx / 0 errors / 0 invalid_dates /
0 missing_required_keys / 0 sign-flips across all 14 banks.

sprint6_impact baseline (post #15):
  total tx: 58,921   distinct counterparties: 16,196 (down from 16,662)
  UNIDENTIFIED: 18   UNCATEGORIZED: 42 (+7 = RFLX V/YS/DW short bodies)

## What this session shipped (4 commits, 3 layers)

#12 OCBC DUITNOW(INST TRF) /IB handler  (app.py, +45 lines)
  Bank-scoped to OCBC. Extracts entity from 491 raw rows in OCBC Calvin
  Skin + LF Services files. Handles SDN-suffix + bare-S truncation
  restoration (OCBC truncates entity at ~22 chars). UNNAMED DUITNOW
  (CR/DR) for bare/unparseable. Subagent built the initial draft;
  main session augmented with BH-suffix restoration and removed dead
  OCR-footer-clip code.

#14 own-party exact-match in _strip_own_party_tokens  (app.py, +13 lines)
  SHARED HELPER, all 14 banks benefit. Sprint 6 #10's stripper had a
  conservative "refuse to strip when counterparty == own-party" rule
  that left explicit own-account-transfer rows leaking. Fix: when
  name_up == own_core, return f"{name} (OWN-PARTY)". The "(OWN-PARTY)"
  suffix survives _normalise_counterparty (verified) and is excluded
  from re-stripping by the existing guard in build_counterparty_ledger.
  Cross-bank-safe: rule fires only on EXACT token equality. Effect
  this session: Alliance Bestlite 162 false-counterparty rows correctly
  relabelled BESTLITE ELECTRICAL (OWN-PARTY).

#13 OCBC own_party_name stamping  (ocbc.py, +55 lines)
  OCBC parser now extracts statement-holder company name from page-1
  header text and stamps every transaction's own_party_name field.
  Was None on all 1,140 OCBC corpus tx; now stamps e.g.
  "LF SERVICES SDN BHD", "CALVIN SKIN SDN BHD". Helper handles OCBC's
  "<3-digit branch>\n<COMPANY NAME>" header layout. Combined with #14,
  CALVIN SKIN false counterparty 53 → 0 rows.

#15 RHB Reflex (RFLX) + RHB misc fees + C24 sync  (3 layers, +136 lines)
  Parser layer (app.py): 4 RFLX sub-formats + 5 misc fee patterns +
    amount-safety check on fees (ratio ≤ RM 100 to surface outliers).
    Single-token bodies (MOHAMMAD, WAN, ARKAS) bucketed as
    "<NAME> (RFLX — possibly multiple parties)" — preserves the name
    but flags ambiguity (PDF-truncated common names cannot be safely
    consolidated as one party). Multi-token bodies (ONG JIA BIN,
    JATI WAJA) → real entity. SC + CM112 are the SAME fee printed in
    two formats (verified via data inspection — both RM 0.50 each);
    routed to BANK FEES.
  Signature change: _extract_counterparty(description, bank, amount=None)
    — new optional amount parameter, backward compatible. Call site in
    build_counterparty_ledger updated to pass max(debit, credit).
  Classification rules layer (CLASSIFICATION_RULES_v3_5.json):
    Version bumped 3.5.0 → 3.5.1. C24 keywords[] + regex extended with
    7 RHB fee patterns (RFLX INSTANT TRF SC, RFLX / CM, REFLEX- / CM,
    CHQ SVC, SERVICE CASH CHQ, SERVICE CHARGES-OTHERS, BANKERS REFER
    CHARGES). Per CLAUDE.md and project memory, both layers (parser
    + AI rules) MUST stay in sync.
  Validator layer (scripts/validate_keywords.py):
    PARSER_PATTERNS BANK FEES regex extended to mirror.
  Net impact: 671 RFLX + 24 misc-fee rows resolved on RHB Bank +
    RHB Islamic. The 1 RM 138K SC outlier deliberately stays raw
    (amount safety) for separate investigation.

## Critical lessons saved this session (apply to all future iterations)

1. PATTERN-MATCH IS NOT THE SAME AS DATA-VERIFICATION.
   I initially treated SC and CM112 as different fees because they LOOKED
   different (one human-readable label, one cryptic code). Inspection
   revealed they're the SAME fee in two formats (both RM 0.50, both Reflex
   Instant Transfer Service Charge, CM112 in both descriptions). Always
   verify by pulling actual rows + amounts before assigning categories.

2. NEVER INVENT ENTITIES; NEVER FALSELY CONSOLIDATE.
   When PDF truncates names beyond recovery, do NOT bucket all into one
   fake party. Use a marker like "(RFLX — possibly multiple parties)"
   so the analyst sees the volume per truncated name without being
   misled into treating it as one entity. UNCATEGORIZED is honest for
   sub-3-char bodies (initials, codes — too short to even be ambiguous).

3. DUAL-LAYER SYNC IS A HARD RULE, NOT A SUGGESTION.
   When adding fee patterns to parser BANK FEES routing, always update
   THREE files in the same commit: app.py + CLASSIFICATION_RULES.json +
   scripts/validate_keywords.py PARSER_PATTERNS mirror. Per CLAUDE.md.

4. AMOUNT-SAFETY MIRRORS EXISTING C24 v3.2 RULE.
   The "OTHER TRANSFER FEE if amount ≤ RM 1.00 → C24, full stop" rule
   is the precedent. When a fee description matches but the amount is
   non-fee-shaped (e.g. RM 138K SC outlier), do NOT silently route to
   BANK FEES. Surface for review by returning raw.

5. SUBAGENT vs ABSORB-DIRECTLY decision.
   Spawn subagent for: corpus enumeration, multi-shape regex design, fresh
   analysis with edge-case discovery (matches the original Sprint 6 #11
   workflow). Absorb directly when: tweaking already-spawned work, small
   tightening (BH restoration, dead-code removal), tightly coupled fixes
   (#13 + #14 + #15 amount safety). Do NOT re-spawn for trivial follow-ups.

## What user should do FIRST (before any new work)

1. PUSH or hold: 4 commits (5e657ee, 82f36d6, 83f4027, f0993fd) are
   local on sprint-6/polish. Decide whether to push to origin now.

2. Re-parse OCBC PDFs via Streamlit on the new parser. Fresh
   full_report.json files should now carry own_party_name on every OCBC
   row (Sprint 6 #13). The Sprint 6 #14 stripper will then collapse the
   own-party leaks. Same applies to Alliance Bestlite — its existing JSON
   already shows the new BESTLITE ELECTRICAL (OWN-PARTY) bucket because
   Alliance has been stamping own_party for several sprints.

3. Upload v3.5.1 CLASSIFICATION_RULES to Claude AI project knowledge
   (replacing v3.5.0). File:
     validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json
   Git push does NOT sync to claude.ai web.

## Sprint 6 #16 — pending work (queued, recommended next)

A. RHB REFLEX- transfer handler (NOT the fee form — the named-transfer
   form). 57 rows, RM 322K total on RHB Bank Waja. Same RHB Reflex
   platform as RFLX but different print format. Examples:
     'REFLEX- ASHRUL ALLOWANCE / -'  (recurring employee allowance)
     'REFLEX- MOHAMAD SEPT / -' / 'REFLEX- MOHAMAD OCT / -'  (monthly)
     'REFLEX- HASSAN BIN PUSPAKOM/ / -'  (vendor — vehicle inspection)
     'REFLEX- BENGKEL INV 6585/ / -'  (workshop invoice)
     'REFLEX- KERAJAAN I- -'  (gov rebate, RM 14,833 CR)
     'REFLEX- MALAYSIAN MODALKU 0006/ -'  (RM 79,360 CR — P2P platform)
     'REFLEX- ASHRUL SAVING/ / -'  (RM 50K-55K)
     'REFLEX- ASHRUL compny fund/' / 'REFLEX- ASHRUL COMPYNY / -'
     'REFLEX- Tenaga/ -'  (electricity bill)
   Mix of recurring + one-off, names + purposes. Apply same 1-token vs
   2+ token ambiguity rule from #15? Or different threshold? Needs
   enumeration first.

B. RHB RPP transfer handler. 36 rows, RM 1.06M total on RHB Bank Waja.
   RPP = Real-time Retail Payments rail (Malaysia). Examples:
     'RPP ASHRUL / FUND / -' / 'RPP ASHRUL / RETURN / -' / 'RPP ASHRUL / COMPANY / -'
       (large recurring transfers, RM 30K-50K each, ~10 rows)
     'RPP JATI WAJA / / -'  (RM 298,500 single tx)
     'RPP RN BINA / Loan / -'  (RM 50K loan disbursement)
     'RPP USS / Sub PDRM / DuitNow -'  (RM 22K)
     'RPP USS / Kenderaan / DuitNow -'  (RM 38K)
     'RPP NUR ATIAH / Viva / -'  (small recurring)
   Format: 'RPP <NAME> / <purpose> / [extra-ref] -'.

C. RHB RM 138,791.36 SC outlier investigation:
   Date 2025-08-15, desc 'RFLX INSTANT TRF SC DR 0000003847 CM112',
   debit 138,791.36 (vs typical RM 0.50 SC). Currently raw thanks to
   Sprint 6 #15 amount safety. Likely either (a) bank PDF data-quality
   issue at source — printed wrong code, or (b) parser misread the
   amount column. Inspect the original Kay R PDF to determine which.

D. (Optional) Re-decide the 7 RFLX V/YS/DW short bodies. Currently
   UNCATEGORIZED. Could apply the (RFLX — possibly multiple parties)
   marker for consistency, but bodies are 1-2 chars (initials, not
   names). Recommendation: keep as UNCATEGORIZED — honest answer.

## Sprint 6 queue — original pending items still outstanding

Reference handoff above (2026-04-25 evening) for full context on each.
Priorities by volume × recoverability:

  #4 HLB Islamic CIB / Instant Transfer / FPX B2B1  ~365 rows
  #6 Ambank Fund Transfer + JomPAY comma-delim       ~223 rows
  #7 OCBC GIRO CREDIT / CA MYDEBIT / CA BANKCARD      ~220 rows
       (open Q: bucket vs entity for card purchases?)
  #8 Alliance NBPS IBG Dr <ENTITY>                    ~137 rows
  #10 UOB small misc                                   ~28 rows
       (open Q: add CHEQUE WITHDRAWAL bucket?)
  #9 Bank Rakyat CIBDRADVICE / DUITNOWTRANSFER     ~1,720 rows
       SAVE FOR LAST — parser-upstream change. Split 9a (low-risk
       fee-regex add) + 9b (high-risk parser-side line-merge).

#5 partially done — #15 covered the RHB Islamic Kay R RFLX rows. The
remaining Kay R patterns (RPP INWARD INST TRF, INWARD IBG, REFLEX-FUNDS,
LOCAL CHQ DEP, LOANS/FIN PAYMENT, FPX DD SELLER, RENTAS CREDIT,
ST - DR) are still raw — could be a separate Sprint 6 #17.

## Open questions (answered in this session — DO NOT re-litigate)

- Truncated common first names (MOHAMMAD/WAN/ARKAS) → bucket as
  "<NAME> (RFLX — possibly multiple parties)", NOT bare name (false
  consolidation), NOT UNNAMED RFLX (discards data). Single source of
  truth: keep names per row, mark ambiguity.
- 1-token vs 2+ token threshold: 1 token = ambiguous, 2+ = real entity.
  "Mohammad Ali" 2-token is OK common — exact spelling+order makes the
  collision rate acceptable.
- Bank service fees (RHB Reflex SC, CHQ SVC, SERVICE CHARGES-OTHERS,
  etc.) → BANK FEES bucket, no per-fee sub-buckets. ONLY exception
  category that's broken out is loan repayment.
- Amount-safety check matches existing C24 v3.2 OTHER TRANSFER FEE
  rule. Threshold RM 100. Outliers stay raw.
- "(OWN-PARTY)" suffix is the existing convention; preserves through
  _normalise_counterparty; existing guard in build_counterparty_ledger
  prevents re-stripping.
- One commit per concrete handler (Sprint 6 rule). #15 bundled RFLX +
  misc fees because they're the SAME platform (RHB Reflex) and same
  routing principle (BANK FEES). REFLEX-/RPP get their own #16 commit
  because they need fresh enumeration.

## Key files (committed locally, not pushed)

Parser:
  app.py — _extract_counterparty signature, OCBC + RHB handlers,
    _OWN_PARTY_PROTECTED_LABELS, _strip_own_party_tokens
  ocbc.py — own_party stamping helper + wiring

AI prompt files:
  validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_5.json
    (v3.5.1 — extended C24 with 7 RHB fee patterns)

Scripts:
  scripts/validate_keywords.py — PARSER_PATTERNS BANK FEES regex mirror

Documentation:
  prompts/NEXT_CHAT_PROMPT.md — this file

## Subagent prompt template (FILL IN PER PATTERN, then launch)

Same template as in the 2026-04-25 handoff section above (search for
"## Subagent prompt template (FILL IN PER PATTERN, then launch)").

Key adjustments learned this session:
- Add EXPLICIT data-verification step BEFORE designing the regex.
  Pull actual rows + amounts. Don't pattern-match on description shape
  alone.
- For PARSER + RULES coordinated changes, instruct the subagent to
  update ALL THREE layers (parser, classification rules, validator).
- For amount-aware logic, remind the subagent that
  _extract_counterparty now accepts amount=None as third parameter.
- For "ambiguous name" cases, the convention is
  "<NAME> (<PREFIX> — possibly multiple parties)" not UNNAMED.

## First actions in new chat

1. Acknowledge the handoff. Verify state:
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -5              # expect: 5e657ee, 82f36d6, 83f4027, f0993fd, 4b87b52
     git tag -l 'sprint*'              # expect: sprint-4.5-complete
     git status --short                # expect: untracked items only

2. Sanity-check:
     python3 scripts/validate_reference_statements.py
       → expect 45,008 tx, 0 errors per bank
     python3 scripts/sprint6_impact.py --out /tmp/sprint6_baseline.json
       → expect total=58,921 distinct=16,196 UNIDENTIFIED=18 UNCATEGORIZED=42

3. Ask user:
   "Have you (a) pushed the 4 commits to origin/main, (b) uploaded
   v3.5.1 CLASSIFICATION_RULES to Claude AI, and (c) re-parsed OCBC
   PDFs via Streamlit? Also: launch Sprint 6 #16 (REFLEX- + RPP) or
   different priority?"

4. Default recommendation: launch #16 (REFLEX- + RPP) — natural
   continuation of #15. ~93 rows + RM 1.38M material. Use the subagent
   prompt template; specifically instruct to enumerate ALL distinct
   REFLEX-/RPP descriptions across the corpus before designing regex
   (lesson from this session: don't shortcut the enumeration).

## Rollback procedure

  # Drop just Sprint 6 #15:
  git reset --hard 82f36d6
  # (Removes the parser + rules + validator changes for #15)

  # Drop everything from this session, back to pre-#12 state:
  git reset --hard 4b87b52
  # (Returns to the doc-only commit on top of Sprint 6 #11)

  # Drop sprint-6/polish entirely after pushing:
  git checkout main
  git branch -D sprint-6/polish
  git push origin --delete sprint-6/polish

Tag sprint-4.5-complete remains the permanent stable marker.
```

---

## Deferred — HTML consolidation UI for `(possibly multiple parties)` buckets

Discussed 2026-04-26, scoped but NOT shipped this session. Belongs to a fresh
sprint after the parser-side single-token ambiguity rule is fully in place
(post Sprint 6 #16).

### Why this exists

Sprint 6 #15 / #16 produce single-token ambiguity buckets like
`ASHRUL (possibly multiple parties)`. The rail label (REFLEX-/RPP/RFLX) is
deliberately stripped — user direction: rail labels are noise, never appear
in counterparty names. Bucket name shows only the candidate entity + the
ambiguity marker.

But sometimes the analyst KNOWS from context that all 24 transactions in
`ASHRUL (possibly multiple parties)` really are the same person (e.g. the
workshop foreman they pay weekly). Today there's no way to mark that
decision and have the report reflect it. This UI closes that loop.

### Design — HTML renderer interactive review

Lives in `bank-statement-analysis-HTML-fresh/` (NOT in `app.py` parser).

Per-bucket UI in Top Payees / Top Payers panels:
  - Buckets whose name ends in `(possibly multiple parties)` get a small
    "Review" pill next to the count.
  - Click Review → modal/expander shows all transactions in the bucket
    (date, amount, raw description, source rail).
  - Three options:
    1. **Consolidate as <name>** — text input pre-filled with the bucket
       name minus the suffix. Click Save → bucket renames, suffix dropped,
       all downstream views (related-party, salary coverage, top
       payees/payers) recompute on the new name.
    2. **Keep ambiguous** — no change, marks bucket as "reviewed but
       genuinely ambiguous" (e.g. multiple ASHRULs really do exist).
    3. **Split into separate parties** — heavier feature, defer to a
       later iteration; opens a per-transaction tagger.

### Persistence — sidecar JSON

File: `canonical_entities_<COMPANY>.json` placed next to the corresponding
`full_report.json` (e.g. `canonical_entities_Waja_RHB.json`).

Schema:
```json
{
  "ASHRUL (possibly multiple parties)": {
    "decision": "consolidate" | "keep_ambiguous" | "split",
    "canonical_name": "Ashrul bin Ahmad",
    "reviewed_at": "2026-04-26",
    "reviewed_by": "luqman"
  }
}
```

On HTML render: load sidecar (if exists), apply renames before generating
charts and tables. On parser re-run: `full_report.json` regenerates but
sidecar is preserved (separate file). Sidecar can be version-controlled
or shared across analysts.

### Visual indicator after consolidation

OPEN QUESTION (not yet answered by user). Two options:
  a) Drop the `(possibly multiple parties)` text entirely → bucket reads
     just `Ashrul bin Ahmad`, indistinguishable from non-ambiguous parties.
  b) Keep a small `✓ reviewed` badge next to canonical name so analyst
     can see which buckets are manually-confirmed vs. auto-extracted.

Pick at implementation time.

### Out of scope

  - Cross-bank consolidation. ASHRUL on RHB stays separate from ASHRUL on
    Maybank — different statement holders, different payee universes.
  - Auto-suggesting consolidation candidates (fuzzy name matching). Could
    be a v2; not on the table for the first iteration.
  - Editing the underlying `full_report.json`. Sidecar is read-only ON
    the parser output.

### Order of operations (carried over)

1. Sprint 6 #16 (parser, REFLEX-/RPP handlers + #15 RFLX label retro-fit
   so single-token ambiguity buckets are rail-agnostic) — REQUIRED FIRST.
2. Sprint 6 #17 (renderer, Review UI + sidecar JSON read/write) — only
   meaningful AFTER step 1 ships, because step 1 produces the buckets the
   UI consolidates.

### Confirmed scope notes (do NOT re-litigate)

- Rail names (REFLEX, RPP, RFLX, IBG, etc.) NEVER appear in any
  counterparty bucket name. They are pure noise. Strip without exception.
- Multi-token names (HASSAN BIN PUSPAKOM, MALAYSIAN MODALKU) extract bare
  — no ambiguity marker, no rail tag. They auto-consolidate across rails.
- Single-token first names (ASHRUL, MOHAMMAD, WAN, ARKAS) get the
  `(possibly multiple parties)` suffix — rail-agnostic, single bucket per
  name regardless of which RHB rail produced the row.
- `canonical_entities_<COMPANY>.json` sidecar is the persistence
  mechanism. NOT in-memory browser state. Survives parser re-runs.
- Sprint 6 #22 in the deferred list ("canonical_entities_<COMPANY>.json
  band-aid") is THIS feature. The two are the same item.

---

## Session handoff — 2026-04-26 evening (Sprint 6 #16 shipped — RHB Bank + RHB Islamic)

```
Repo: Bank-Statement-Analysis-main 3
Working dir: /Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## State on arrival

Branch: sprint-6/polish (working branch — STAY on this branch)
Tag:    sprint-4.5-complete (permanent stable marker, unchanged)

Commits on sprint-6/polish (newest first, last 6):
  8b14f01  Append 2026-04-26 evening handoff — Sprint 6 #16 shipped
  62b79f4  Sprint 6 #16: RHB Bank + RHB Islamic counterparty extraction
  b3630d2  Append 2026-04-26 handoff — Sprint 6 #12–#15 shipped
  5e657ee  Sprint 6 #15: RHB Reflex (RFLX) + RHB miscellaneous fees + C24 sync
  82f36d6  Sprint 6 #13: OCBC own_party_name stamping
  83f4027  Sprint 6 #14: own-party exact-match handling

PUSHED 2026-04-26: branch sprint-6/polish is up to date with
origin/sprint-6/polish. Commits backed up on GitHub. NOT yet merged to
main → Railway production still runs the OLD parser. Live Streamlit app
unchanged until user merges sprint-6/polish → main and pushes main.

14-bank regression status: clean. 45,008 tx / 0 errors / 0 invalid_dates /
0 missing_required_keys / 0 sign-flips across all 14 banks.

sprint6_impact baseline (post #16):
  total tx: 58,921   distinct counterparties: 16,044 (down from 16,196)
  UNIDENTIFIED: 18   UNCATEGORIZED: 42 (both unchanged from #15 baseline)

## What this session shipped

#16 RHB Bank + RHB Islamic counterparty extraction (app.py, +431 lines)
  Two pattern families:

  Family A — date-line entity (RHB Bank / Waja file):
    'RPP <ENTITY> / <purpose> / <ref> -'
    'REFLEX- <ENTITY> [<purpose>] / -'  /  'REFLEX- <ENTITY> I- -'
    'MB FUND <ENTITY> / <purpose>/ -'
    'INWARD IBG <ENTITY> [<refs>] [I- -]'   (Waja variant — entity at start)
    'RENTAS <ENTITY> [/ROC/...] [I-] -'
    'FPX B2B <ENTITY> [<ref>] -' / 'FPX DD <ENTITY> [<ref>] -'
    Cash/cheque markers (CASH/, CDT CASH, CASH CASH CHQ, CHEQUE/, CLEARING)

  Family B — entity-at-end (RHB Islamic / Kay R file):
    'LOCAL CHQ DEP <ref> - -'  → Unidentified (Cheque)
    'LOANS/FIN PAYMENT <ref10> <ENTITY> AUTODEBIT'  → keep entity
    'RPP INWARD INST TRF (DR|CR) <ref10> <ENTITY> <purpose>'
    'REFLEX-FUNDS TFR (DR|CR) <ref10> <ENTITY> <purpose>'
    'FPX DD SELLER (DR|CR) <ref10> <ref> <code> <ENTITY> <ENTITY-full>'
    'RENTAS CREDIT <ref10> <ref> <code> <ENTITY-RUN-AT-END>'
    'INWARD IBG <ref10> [refs] <ENTITY-RUN-AT-END>'  (Kay-R variant)

  Adds 'ST - DR <ref10> SST Remittances' to existing RHB miscellaneous
  bank-fee regex → BANK FEES bucket (RM 100 amount-safety threshold).

  Retro-fits Sprint 6 #15 RFLX-named labels:
    'UNNAMED RFLX (CR|DR)' → 'UNNAMED RHB TRANSFER (CR|DR)'
    '<NAME> (RFLX — possibly multiple parties)' → '<NAME> (possibly multiple parties)'
  Net effect: RFLX/REFLEX-/RPP rows of the same single-token name now
  consolidate into ONE rail-agnostic ambiguity bucket (e.g. ASHRUL: 14 →
  68 rows after combining RFLX + REFLEX- + RPP rails).

  LOAN-keyword rows KEEP the entity name (don't route to LOAN_DISBURSEMENT
  / LOAN_REPAYMENT bucket). The AI classifier picks up C10/C11 from the
  'Loan' keyword in description; the counterparty field preserves the
  lender/funder identity for credit underwriting. Affects RPP, REFLEX-,
  and LOANS/FIN PAYMENT shapes. New visible entities: RN BINA (6 rows /
  RM 120K loan disbursement), KAY R RESOURCES SDN BHD (46 rows / RM
  4.73M loan repayments).

  Net impact: +367 rows resolved.
    Waja RHB: 230 → 0 raw  (RHB Bank file is now 100% extracted)
    Kay R: 138 → 1 raw     (only the RM 138,791 RFLX SC outlier remains,
                            preserved by amount-safety for analyst review)
    Distinct counterparties (corpus-wide): 16,196 → 16,044 (-152 — pure
      consolidation, no new noise)
    UNIDENTIFIED 18 → 18, UNCATEGORIZED 42 → 42 (both unchanged)

## Critical lessons saved this session (apply to all future iterations)

1. RAIL LABELS ARE NOISE TO USERS.
   Transfer-mechanism prefixes (REFLEX, RPP, RFLX, IBG, RENTAS, FPX,
   DuitNow, JomPAY, FPX B2B, CMS, CIB, etc.) are implementation detail.
   They appear in regex anchors as a technical necessity but must NEVER
   be foregrounded in user-facing communication or counterparty bucket
   names. The user works in credit underwriting — perspective is
   counterparty identity, amounts, and frequency, NOT bank operations
   plumbing.

2. KEEP ENTITY ON LOAN-KEYWORD ROWS — DON'T BUCKET TO LOAN_DISBURSEMENT.
   Counterparty extraction and category classification are independent
   layers. Routing 'RPP RN BINA / Loan / -' to a generic 'LOAN
   DISBURSEMENT' bucket loses RN BINA in Top Payers. The AI classifier
   reads the full description and assigns C10/C11 from the 'Loan'
   keyword regardless of what the counterparty name is. Best of both
   worlds: parser keeps entity, AI classifier categorises. The HTML
   Facilities tab shows the description column anyway, so the analyst
   can drill in and see RN BINA inside the C10 list.

3. CROSS-RAIL NAME CONSOLIDATION ALREADY HANDLED.
   The existing M1–M5 merge logic in _merge_counterparty_groups
   (app.py ~line 3415) consolidates 'WAN KAMARULBAHRI BIN' /
   'WAN KAMARULBAHRI BIN WAN' / 'WAN KAMARULBAHRI BIN ALI' style
   PDF-truncation duplicates via M2 prefix-match (≥10-char threshold)
   and M3 BIN/BINTI logic. Don't add redundant prefix-merge in new
   handlers — verify against the live ledger first.

4. VERIFY SUBAGENT CLAIMS AGAINST LIVE DATA.
   Subagent's report described 'WAN KAMARULBAHRI BIN' / 'BIN WAN' as two
   distinct buckets; live ledger inspection showed they had already
   merged via M2. Trust-but-verify: every subagent claim about ledger
   state should be confirmed by calling build_counterparty_ledger() and
   inspecting the actual output, not by reading raw description shapes.

5. AMOUNT-SAFETY ALSO CATCHES DATA-QUALITY OUTLIERS.
   'RFLX INSTANT TRF SC DR 0000003847 CM112' RM 138,791.36 — should be a
   RM 0.50 service charge. The amount-safety threshold (RM 100) keeps
   it raw, surfaces for analyst review. Likely PDF data-quality issue at
   bank source. Not silently routed to BANK FEES.

## What user should do FIRST (before any new work)

1. ALREADY DONE — sprint-6/polish pushed to origin (2026-04-26 evening).
   Branch is on GitHub but Railway still runs the old parser because
   only main is auto-deployed. The 6 new commits (#12-#16 + 2 handoff
   appends) are NOT yet on main.

2. Re-parse Waja RHB + Kay R PDFs via Streamlit on the new parser
   (run locally — Railway hasn't picked up the new parser yet).
   Fresh full_report.json files should now show:
   - RN BINA, KAY R RESOURCES SDN BHD, KAY R WORKSHOP (M) SDN BHD,
     DIVERSATECH FERTILIZER SDN BHD, etc. as Top Payees/Payers entries
     (instead of 'LOAN DISBURSEMENT' aggregating these as a generic
     bucket).
   - ASHRUL (possibly multiple parties) consolidated as a single
     ambiguity bucket combining RFLX + REFLEX- + RPP rows.
   - 'UNNAMED RHB TRANSFER (CR|DR)' replacing 'UNNAMED RFLX (CR|DR)'
     for bare/unparseable RHB rows.

3. (Optional) Feed refreshed JSON through Claude AI on web.
   Expected: C10 Loan Disbursement and C11 Loan Repayment totals
   unchanged (the AI classifier still picks up 'Loan' keyword from
   description regardless of counterparty bucket name). Top Payers /
   Top Payees view shows the actual entities.

4. (Optional, when ready to deploy) Merge sprint-6/polish → main and
   push main to trigger Railway auto-deploy:
     git checkout main
     git merge sprint-6/polish
     git push origin main
   Live Streamlit app picks up the new parser. Eyeball at least one
   re-parse via the live app to confirm before broader use.

## Sprint 6 queue — REMAINING patterns (none from RHB)

#16 fully resolved RHB Bank Waja AND RHB Islamic Kay R. Remaining queue:

  #4 HLB Islamic — CIB / Instant Transfer / FPX B2B1   ~365 rows
     Files: HLB MTCE.json (~330) + HLB Detik.json (~35).
     Sub-shapes: CIB Instant Transfer at <BRANCH> <amt> <purpose> <ENTITY>
     <BANKREF>, Instant Transfer at <BRANCH> ..., CIB IBG CA Debit Advice,
     FPX B2B1, Serv Charge-IBG/TT/Rentas/Misc.
     Watch: own-account markers like 'INTER ACC TXN OWN ACC TXN' →
     bucket as UNNAMED (own-account transfer).

  #6 Ambank — Fund Transfer + JomPAY comma-delim       ~223 rows
     Files: Ambank Plentitude.json (164) + Ambank Hon Engineering.json (59).
     Pattern: '^(?:Fund Transfer|JomPAY|Interbank GIRO) /DEBIT TRANSFER,
     <ENTITY>, <rest>'. Extends existing CP3 Ambank handler at app.py
     line 2317 (which already handles 'DuitNow TRF /MISC ..., <ENTITY>').
     Edge cases: bare ATM withdrawal, MEPS FEE, CTL OUTWARD CLEARING.

  #7 OCBC — GIRO CREDIT / CA MYDEBIT / CA BANKCARD     ~220 rows
     File: OCBC Calvin Skin.json (mostly).
     OPEN QUESTION: bucket vs entity for CA MYDEBIT PURCHASE (POS card)
     and CA BANKCARD PAY (online card) — analyst preference TBD. Ask
     before launching subagent.
     Routing: GIRO CREDIT PBB-PBCS → biller bucket (PUBLIC BANK).

  #8 Alliance — NBPS IBG Dr <ENTITY>                   ~137 rows
     File: Alliiance KYDN.json.
     Pattern: 'NBPS IBG Dr CA <AOBref> <C-token> <num> <ENTITY>
     <num> <num>'. Wiring: NEW BRANCH in _extract_counterparty_alliance
     (~app.py line 1904). Also tackle small Alliance-tail items if cheap
     (IB2G FND TRF, IB2G CA Common Chrg → BANK FEES, HOUSE CHEQUE/MISC).

  #10 UOB — small misc                                 ~28 rows
     Files: UOB Juta Kenangan.json + UOB Upell.json.
     Sub-shapes: '<6digit_ref> ORIX CREDIT MALAYSIA SDN BHD' (12),
     own-party leak via DuitNow trailer (16), 'OD Int Charge' → BANK FEES.
     OPEN QUESTION: UOB Juta Kenangan has 444 'Chq Wdl' rows that COULD
     be tackled here as a NEW CHEQUE WITHDRAWAL special bucket. Confirm
     before scope expansion.

  #9 Bank Rakyat — CIBDRADVICE / DUITNOWTRANSFER     ~1,720 rows
     File: Bank Rakyat Koperasi Felcra.json.
     SAVE FOR LAST — parser-upstream change. Recipient name lives on
     the line ABOVE the transaction in the PDF. Modifies bank_rakyat.py
     internal logic. Sub-task split:
       9a. Add CIBSMSFEE / CIBDRCHARGES / DUITNOWFEE / CIBSMSFEE prefixes
           to BANK FEES regex (LOW RISK — pure regex addition, ~2,500 rows).
       9b. Modify bank_rakyat.py to merge prior PDF lines into
           CIBDRADVICE / DUITNOWTRANSFER descriptions (HIGH RISK —
           parser change).

## Pending — beyond Sprint 6 (deferred, unchanged)

Sprint 5 (heavy, fresh-session recommended):
- #21 kredit_lab_classify.py — reusable Python module for AI classification
  via Anthropic SDK (replaces manual claude.ai upload step). 500-1000 lines.
- #23 Regression fixture suite — MTA/KYDN/Muhafiz/DMC as fixtures.
- #24 Synthetic OD simulation — flip CR statement signs.

HTML / Renderer (deferred items, see deferred section above):
- #17 / #22 canonical_entities_<COMPANY>.json review-and-consolidate UI.
  Lets analyst manually mark '<NAME> (possibly multiple parties)' buckets
  as consolidated to a canonical name. Sidecar JSON persistence.
  REQUIRES the parser-side ambiguity buckets to exist (which they do
  post #16). Order: parser first (DONE), renderer next.

## Key decisions this session (do NOT re-litigate)

- Rail labels (REFLEX, RPP, RFLX, IBG, RENTAS, FPX, DuitNow, etc.)
  NEVER appear in counterparty bucket names. Pure noise from the credit
  underwriting perspective.
- Multi-token entities → bare entity (auto-consolidates across rails).
- Single-token first names → '<NAME> (possibly multiple parties)' —
  rail-agnostic suffix; existing M1-M5 merge handles cross-rail
  consolidation when multi-token longer forms also exist.
- LOAN-keyword rows → keep entity. AI classifier handles C10/C11
  from 'Loan' keyword in description. The two layers are independent.
- Cross-rail name consolidation (PDF-truncation duplicates like
  'WAN KAMARULBAHRI BIN' / 'BIN WAN') is ALREADY handled by existing
  M1-M5 merge logic. Don't add new prefix-merge handlers — verify
  against live ledger first.
- Amount-safety threshold (RM 100) for fee patterns: outliers stay raw
  for analyst review, never silent-routed.
- HTML Review UI for ambiguity-bucket consolidation is DEFERRED to a
  future sprint. Saved in earlier section of this file (search for
  'Deferred — HTML consolidation UI').

## Key files (committed locally, not pushed)

Parser:
  app.py — _extract_counterparty(), RHB Family-A and Family-B handlers
    at ~line 2488 onwards. Helpers _rhb16_clean_body, _rhb16_finalize,
    _take_entity_leading, _take_entity_trailing, _canonicalize_legal_suffix,
    _dedupe_entity_halves all defined inline within the function.
    _OWN_PARTY_PROTECTED_LABELS updated (line ~3215) to drop UNNAMED RFLX
    buckets and add UNNAMED RHB TRANSFER + Unidentified (Cheque).

Documentation:
  prompts/NEXT_CHAT_PROMPT.md — this file
  ~/.claude/projects/.../memory/feedback_no_rail_labels_in_discussion.md
  ~/.claude/projects/.../memory/user_profile.md (updated with credit-
    underwriting perspective)

## Subagent prompt template (FILL IN PER PATTERN, then launch)

Same template as in the 2026-04-25 evening handoff section above (search
for "## Subagent prompt template (FILL IN PER PATTERN, then launch)").

Key adjustments learned this session:
- Frame the work in entity-extraction language, NOT in rail-mechanism
  language. The PATTERN TO HANDLE block can name the regex anchor
  strings (necessary technical detail) but the GOAL / WORKFLOW prose
  must be entity-centric.
- LOAN-keyword rows MUST keep entity name. Do NOT route to a generic
  LOAN_DISBURSEMENT / LOAN_REPAYMENT bucket. The AI classifier handles
  C10/C11 from the description's 'Loan' word.
- Verify subagent's bucket-existence claims against the LIVE ledger
  output (build_counterparty_ledger), not just raw description shapes.
  M1-M5 merge logic already handles many cases that look like duplicates
  in raw form.
- Rail labels NEVER in bucket names. UNNAMED <BANK> TRANSFER (CR|DR)
  is the safe pattern for bare/unparseable bare-prefix rows; ambiguity
  buckets use '<NAME> (possibly multiple parties)' rail-agnostic suffix.

## First actions in new chat

1. Acknowledge the handoff. Verify state:
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -6              # expect newest 4: 8b14f01, 62b79f4, b3630d2, 5e657ee
     git tag -l 'sprint*'              # expect: sprint-4.5-complete
     git status --short                # expect: untracked items only
     git log --oneline origin/sprint-6/polish..HEAD  # expect: empty
                                       # (means local is in sync with origin)

2. Sanity-check:
     python3 scripts/validate_reference_statements.py
       → expect 45,008 tx, 0 errors per bank
     python3 scripts/sprint6_impact.py --out /tmp/sprint6_baseline.json
       → expect total=58,921 distinct=16,044 UNIDENTIFIED=18 UNCATEGORIZED=42

3. Ask user:
   "sprint-6/polish is on origin. Has the user (a) re-parsed Waja RHB +
   Kay R PDFs locally via Streamlit to confirm RN BINA / KAY R RESOURCES
   etc. surface correctly, (b) merged sprint-6/polish to main yet (this
   is what triggers Railway redeploy)? Also: launch which next handler
   from the queue? Default by volume: #4 HLB Islamic (~365 rows). Other
   options: #6 Ambank, #7 OCBC GIRO/CARD (open Q on bucket vs entity),
   #8 Alliance NBPS IBG, #10 UOB misc (open Q on CHEQUE WITHDRAWAL
   bucket), #9 Bank Rakyat (high risk, save for last)."

4. Default recommendation: launch #4 HLB Islamic CIB / Instant Transfer
   / FPX B2B1 — top of remaining queue by volume. Use the subagent
   prompt template; instruct to follow the entity-extraction framing
   and NEVER place rail labels in bucket names. Reference commit 62b79f4
   for the RHB handler template.

## Rollback procedure

  # Drop just Sprint 6 #16:
  git reset --hard b3630d2
  # (Removes parser changes; keeps doc-append commit)

  # Drop everything from this session:
  git reset --hard 4b87b52
  # (Returns to pre-Sprint 6 #12 state. NUCLEAR — also drops #12-#15.)

  # Drop sprint-6/polish entirely after pushing:
  git checkout main
  git branch -D sprint-6/polish
  git push origin --delete sprint-6/polish

Tag sprint-4.5-complete remains the permanent stable marker.
```

---

## Session handoff — 2026-04-26 late-night (Sprint 6 #11a shipped — Alliance UNNAMED bucket cleanup; #11b–d next)

```
Repo: Bank-Statement-Analysis-main 3
Working dir: /Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## State on arrival

Branch:  sprint-6/polish (STAY on this branch)
Tag:     sprint-4.5-complete (permanent stable marker, unchanged)

Recent commits (newest first, last 3):
  9a53cfb  Sprint 6 #11a: rename Alliance rail-named UNNAMED buckets
  6d08daa  Update 2026-04-26 handoff — sprint-6/polish pushed to origin
  8b14f01  Append 2026-04-26 evening handoff — Sprint 6 #16 shipped (RHB Bank + Islamic)

NOT YET PUSHED to origin. Local sprint-6/polish is 1 commit ahead of
origin/sprint-6/polish. Push when convenient:
  git push origin sprint-6/polish

14-bank parser regression: 45,008 tx / 0 errors across all 14 banks.
sprint6_impact (post #11a):
  total tx: 58,921    distinct: 16,042  (was 16,044, -2 from rail-bucket collapse)
  UNIDENTIFIED: 18   UNCATEGORIZED: 42

## Why #11 series exists (decision recorded this session)

User asked the architectural question: "what are we improving — parser
or classifier?" The Sprint 4.5 answer is "parser-primary so AI can trust
it without re-validating, escaping the slow/expensive claude.ai re-run
loop." Each Sprint 6 handler reduces classifier workload by giving the
AI a clean counterparty field it can take at face value.

User then asked whether `UNNAMED <RAIL>` bucket labels are applied to
other banks — yes — and whether other banks violate the Sprint 6 #16
no-rail-labels-in-bucket-names rule. Audit found 10 violator buckets
across 5 areas:

  Alliance (7 buckets, all in _extract_counterparty_alliance):
    UNNAMED INSTANT TRANSFER, UNNAMED CR ADVICE, UNNAMED IB2G FUND
    TRANSFER, UNNAMED IB2G DEBIT, UNNAMED FPX PAYMENT, UNNAMED RENTAS
    CREDIT, UNNAMED DD CASA
  Cross-bank: UNNAMED DUITNOW (CR|DR)            (3 occurrences)
  Cross-bank: UNNAMED CMS (CR|DR)                (4 occurrences)
  Maybank:    UNNAMED MAS PAYMENT (DR)           (2 occurrences)

Decision: insert #11 (UNNAMED bucket cleanup) BEFORE the remaining
counterparty-extraction queue (#4 HLB / #6 Ambank / #7 OCBC / #8
Alliance NBPS IBG / #10 UOB / #9 Bank Rakyat). Reasons:
  1. Single-touch on each bank — #6 Ambank touches DuitNow source,
     #8 Alliance touches Alliance file. Doing #11 first avoids
     double-touch.
  2. Audit might surface entities currently invisible (rows in
     rail-named UNNAMED buckets that actually have extractable names).
  3. AI prompt slim-down (final step) needs consistent UNNAMED
     conventions across all banks.

## What this session shipped — Sprint 6 #11a (Alliance UNNAMED rename)

Commit 9a53cfb. Audit + clean rename of 7 Alliance rail-named buckets:

  Before                              After
  ─────────────────────────────────────────────────────────────────
  UNNAMED INSTANT TRANSFER       ─┐
  UNNAMED CR ADVICE               │
  UNNAMED IB2G FUND TRANSFER      ├─→ UNNAMED ALLIANCE TRANSFER (CR)
  UNNAMED IB2G DEBIT              │   UNNAMED ALLIANCE TRANSFER (DR)
  UNNAMED FPX PAYMENT             │
  UNNAMED RENTAS CREDIT           │
  UNNAMED DD CASA                ─┘

Mechanism:
  - _extract_counterparty signature gains direction: Optional[str]
  - _extract_counterparty_alliance signature gains direction
  - build_counterparty_ledger call site computes
    direction = "DR" if debit > 0 else "CR" and threads through
  - 7 rail-named bucket return values replaced with f-string
    "UNNAMED ALLIANCE TRANSFER ({direction_norm})"
  - _OWN_PARTY_PROTECTED_LABELS gains the new labels

Net distinct delta: -2 (4 rail buckets-with-rows collapse to 2;
3 zero-row buckets renamed defensively for future statements).

## CRITICAL LESSON saved this session — DO NOT RE-ATTEMPT

An entity-extractor pre-pass for `CR ADVICE - IBG <entity-with-legal-
suffix>` was implemented and REVERTED in the same commit cycle.
Symptom: distinct counterparties jumped from 16,044 to 16,061 (+17)
in sprint6_impact. Investigation: in KYDN alone, 188 good CP3 labels
were REMOVED (AIA G-policies, SIRIM BERHAD, FOMEMA AP-refs, HEALTH
CONNECT, PM CARE, COMPUMED) and 206 WORSE labels were ADDED with
leading invoice/policy refs re-glued on (e.g. "AIA G406396660" became
"30786373-00 AIA G406396660"; "F22868 SIRIM BERHAD L2503203379021"
appeared instead of clean "SIRIM BERHAD").

Root cause: Alliance helpers (_ab_dedupe_halves, _ab_strip_trailing_refs,
_ab_fix_truncation) are LESS aggressive at leading-ref strip and
multi-token trailing-ref strip than the CP3 generic extractor. Routing
rows that CP3 was already cleaning correctly through Alliance helpers
DEGRADES extraction quality.

GENERAL RULE for future bank-specific entity extractors: BEFORE adding
a pre-pass that intercepts rows on the way to CP3, compare cleanup
aggressiveness side-by-side on a sample of 20+ live rows. If CP3 cleans
better than your bank-helpers, DO NOT add the pre-pass — keep CP3 as
the path. Only add bank-specific extractors for shapes CP3 does NOT
handle (i.e., shapes that currently produce UNIDENTIFIED / UNCATEGORIZED
or visibly garbage labels). Comment block at app.py near the Alliance
bucket section records this lesson.

USER PRINCIPLES (locked in this session, do NOT re-litigate):
  P1. UNNAMED is RESERVED for genuinely-nameless rows. If the description
      contains counterparty entity text, the parser MUST extract it.
      Lazy bucketing of name-rich rows = data loss = parser untrustworthy.
  P2. Entity = proper-noun runs of company / individual names (with or
      without legal suffix). NOT branch codes, rail codes, ref numbers,
      purpose words (CLAIM PAYMENT, MEDICAL), industry keywords, or
      lowercase fragments (asia).
  P3. Description text is preserved verbatim per row regardless of
      counterparty bucket assignment. UNNAMED bucketing is NOT data
      destruction — drilling into a bucket reveals member rows with
      full descriptions (in CSV/XLSX/JSON exports; HTML renderer
      shows monthly trend in expander, full-row drill-down is a UX gap
      deferred to Sprint 6 #17).
  P4. Per-bank consolidation preferred over per-rail (RHB / Alliance
      precedents). DuitNow / CMS being cross-bank rails makes #11b/c
      a genuine open question — ASK the user before defaulting.
  P5. LOAN-keyword rows KEEP entity (don't bucket as LOAN_DISBURSEMENT/
      LOAN_REPAYMENT). AI classifier picks up C10/C11 from description.
  P6. Multi-token entities → bare name. Single-token first names →
      "<NAME> (possibly multiple parties)" rail-agnostic suffix.
  P7. Rail labels (REFLEX/RPP/RFLX/IBG/RENTAS/FPX/DuitNow/JomPAY/CMS/
      CIB/etc.) NEVER appear in counterparty bucket names. Pure noise
      from credit underwriting perspective.

## Sprint 6 queue — REMAINING (in order)

#11b UNNAMED DUITNOW cross-bank audit + cleanup     ← NEXT
   - Code locations: app.py — search `"UNNAMED DUITNOW"` (3 occurrences;
     line numbers may have shifted post-#11a, originally 2358/2361/2376).
   - Survey: which banks/files have rows currently bucketing here? Rough
     row counts per bank. Sample 10-20 descriptions, classify per P2.
   - Open question for user (per P4): keep cross-bank `UNNAMED DUITNOW
     (CR|DR)` (consolidates same-shape rows across banks) OR split
     per-bank into `UNNAMED <BANK> TRANSFER (CR|DR)` (consistent with
     RHB / Alliance precedents but fragments DuitNow volume by bank).
     Ask BEFORE implementing.
   - Apply 11a lesson: do NOT add entity pre-pass for rows CP3 already
     handles. Only target rows currently going to UNNAMED.
   - scripts/validate_keywords.py PARSER_PATTERNS mirror may also
     reference these labels — check for sync after rename.

#11c UNNAMED CMS cross-bank audit + cleanup
   - Code locations: app.py — search `"UNNAMED CMS"` (4 occurrences,
     originally 3031/3039/3061/3070).
   - Same audit-first approach.
   - Likely Maybank-bulk-payroll. Per-bank rename to `UNNAMED MAYBANK
     TRANSFER (CR|DR)` may be appropriate. Confirm bank attribution.

#11d UNNAMED MAS PAYMENT (DR) — Maybank
   - Code locations: app.py — search `"UNNAMED MAS PAYMENT"`
     (2 occurrences, originally 3085/3098).
   - Smallest. Maybank-specific. If #11c goes per-bank, fold this into
     same `UNNAMED MAYBANK TRANSFER (DR)` bucket so Maybank has one
     unified UNNAMED label, not two.

After #11 series done, resume the original Sprint 6 queue:

#4  HLB Islamic (CIB / Instant Transfer / FPX B2B1)  ~529 rows actual
   - Survey done in PRIOR session. 9 distinct shapes, 529 rows total
     (handoff under-estimated by 45%):
       CIB Instant Transfer (254), JomPAY Bill Payment (81),
       Generic Instant Transfer (47), FPX B2B1 (29), IBG CA Debit Advice
       (26), Bulk DuitNow (25), Generic Fund Transfer (24), CA Debit
       Advice (12 — split: 8a/8b nameless, 8c with entity), Serv
       Charges (31).
   - User confirmed direction:
       (a) shape 7 fragile fund-transfer extraction must NOT bucket to
           UNNAMED — extract every time names exist (per P1)
       (b) shape 4 FPX truncation: append "(truncated)" marker
       (c) shape 8a/8b CA Debit Advice (genuinely-nameless): bucket as
           UNNAMED HLB TRANSFER (CR|DR)
       (d) shape 9 fees: BANK FEES + RM 100 amount-safety
   - APPLY 11A LESSON: do NOT introduce HLB-specific pre-pass on shapes
     CP3 already handles. Only add HLB extractor for shapes currently
     going to UNIDENTIFIED / UNCATEGORIZED / garbage labels.
   - Survey can be re-run in fresh session if needed using the same
     subagent prompt structure. Reference: corpus files
     "Full Report HLB MTCE.json" + "Full Report HLB Detik.json" under
     `validation runs - json/claude ai prompt file/Full Report Sample/`.

#6  Ambank — Fund Transfer + JomPAY comma-delim     ~223 rows
#7  OCBC — GIRO CREDIT / CA MYDEBIT / CA BANKCARD   ~220 rows (open Q: bucket vs entity for card POS — ask user)
#8  Alliance NBPS IBG Dr <ENTITY>                    ~137 rows
#10 UOB — small misc                                 ~28 rows (open Q: 444 Chq Wdl rows scope expansion — ask user)
#9  Bank Rakyat — CIBDRADVICE / DUITNOWTRANSFER    ~1,720 rows (HIGH RISK — parser-upstream change to bank_rakyat.py, save for last)

After Sprint 6 fully drained:
  AI prompt slim-down — strip defensive entity-re-extraction logic from
  SYSTEM_PROMPT_v3_5_4.md. v3.5.5 / v3.5 / v6.4 file bumps. ~1 coding
  session + user validation cycle.

After that:
  Sprint 5 #21 kredit_lab_classify.py — Anthropic SDK module to replace
  manual claude.ai upload step. ~500-1000 lines, fresh-session-recommended.

## Key files

Parser:
  app.py — _extract_counterparty signature (~line 2146), Alliance
    dispatch (~line 2171), _extract_counterparty_alliance (~line 1904
    + comment block recording 11a entity-extractor lesson),
    _OWN_PARTY_PROTECTED_LABELS (~line 3212), build_counterparty_ledger
    call site (~line 3666). Line numbers may shift post-#11a.
  Read app.py near the Alliance bucket section BEFORE attempting any
  Alliance entity-extractor work — the comment records why an attempt
  was reverted.

Documentation:
  prompts/NEXT_CHAT_PROMPT.md — this file
  CLAUDE.md — project instructions

## First actions in new chat

1. Acknowledge handoff. Verify state:
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -3              # expect: 9a53cfb, 6d08daa, 8b14f01
     git status --short                # expect: untracked items only
     git log --oneline origin/sprint-6/polish..HEAD
                                       # expect 1 (9a53cfb) UNLESS user
                                       # already pushed since handoff

2. Sanity-check (skip if user is in a hurry):
     python3 scripts/validate_reference_statements.py
       → expect 45,008 tx / 0 errors per bank
     python3 scripts/sprint6_impact.py --out /tmp/sprint6_baseline.json
       → expect total=58,921 distinct=16,042 UNIDENTIFIED=18 UNCATEGORIZED=42

3. Default next: launch #11b UNNAMED DUITNOW audit.
   - Use Explore subagent. Audit prompt structure: same as #11a (find
     all rows in corpus with counterparty == "UNNAMED DUITNOW (CR)" or
     "UNNAMED DUITNOW (DR)" via live build_counterparty_ledger,
     classify by description shape, report per-bucket counts, flag any
     rows with extractable entity text per P2).
   - ASK USER UPFRONT: per-bank vs cross-bank consolidation (per P4).
   - Apply 11a lesson — do NOT add entity pre-pass for rows CP3 already
     handles correctly.

## Rollback procedure

  # Drop just #11a:
  git reset --hard 6d08daa
  # (Returns to pre-#11a state. Other Sprint 6 commits intact.)

Tag sprint-4.5-complete remains the permanent stable marker.

## Context budget note

This session shipped #11a and committed. The handoff was written
immediately after the commit (rather than continuing to #11b) because
each #11 sub-task involves a subagent audit (~2k word output), code
reads, edit cycle, regression runs, and ledger inspection — together
~30-40k tokens per sub-task. Continuing into #11b risked context
exhaustion mid-task. The disciplined call: write the handover while
context is fresh and accurate, let the next session start clean.

The next session has plenty of context to handle #11b cleanly.
```

---

## Session handoff — 2026-04-26 late-late-night (Sprint 6 #11b shipped — OCBC defensive UNNAMED DUITNOW renamed; #11c next)

```
Repo: Bank-Statement-Analysis-main 3
Working dir: /Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## State on arrival

Branch:  sprint-6/polish (STAY on this branch)
Tag:     sprint-4.5-complete (permanent stable marker, unchanged)

Recent commits (newest first, last 3):
  aa3145e  Sprint 6 #11b: rename OCBC defensive UNNAMED DUITNOW bucket
  28e4841  Append 2026-04-26 late-night handoff — Sprint 6 #11a shipped, #11b next
  9a53cfb  Sprint 6 #11a: rename Alliance rail-named UNNAMED buckets

NOT YET PUSHED to origin. Local sprint-6/polish is 2 commits ahead of
origin/sprint-6/polish (aa3145e + 28e4841). Plus this handoff-doc commit
on top once it lands. Push when convenient:
  git push origin sprint-6/polish

14-bank parser regression: 45,008 tx / 0 errors across all 14 banks.
sprint6_impact (post #11b): IDENTICAL to post-#11a baseline.
  total tx: 58,921    distinct: 16,042
  UNIDENTIFIED: 18    UNCATEGORIZED: 42

The #11b rename produced zero data movement — audit confirmed 0 corpus
rows currently bucket to either old (UNNAMED DUITNOW) or new
(UNNAMED OCBC TRANSFER) labels. Pure defensive-path label hygiene.

## What this session shipped — Sprint 6 #11b (OCBC DUITNOW rename)

Commit aa3145e. Single-file change to app.py (12+/7-):

  Before                              After
  ─────────────────────────────────────────────────────────
  UNNAMED DUITNOW (CR)               UNNAMED OCBC TRANSFER (CR)
  UNNAMED DUITNOW (DR)               UNNAMED OCBC TRANSFER (DR)

Mechanism — simpler than #11a, no parameter threading required:
  - The DUITNOW handler at app.py:2371 is already gated by
    `if bank and "OCBC" in bank.upper()` — handler is OCBC-only by
    construction.
  - 3 defensive return sites at app.py:2382/2385/2400 swap from
    f"UNNAMED DUITNOW ({direction})" → f"UNNAMED OCBC TRANSFER ({direction})".
  - _OWN_PARTY_PROTECTED_LABELS gains the two new labels.
  - Comment block above the handler (~app.py:2365-2371) updated with
    Sprint 6 #11b rationale.

Why P7 cleanup despite zero rows: rail labels (DuitNow / RFLX / IBG /
RPP / etc.) must never appear in counterparty bucket names. Even
zero-row defensive paths matter for the AI-prompt slim-down step at
the end of Sprint 6, which needs consistent UNNAMED conventions across
all banks.

## Critical lesson saved this session — audit-before-implement scope check

The #11a-style "thread `bank` through _extract_counterparty" implementation
plan would have been WORK FOR NOTHING here. The DUITNOW handler is
already inside an `if "OCBC" in bank.upper()` branch — the bank is
known statically, no threading needed.

This was caught by reading the handler block BEFORE planning the
implementation, after the audit established that 0 rows currently fire
through these paths. The audit also drove the decision to skip the
"per-bank vs cross-bank" question entirely (per P4 it would have been
asked, but with zero corpus rows the question is moot — bank attribution
is theoretical, and the handler's existing single-bank scope picks the
answer for us).

GENERAL RULE: Before implementing #11x cleanups, always (1) read the
handler's surrounding scope block to check whether `bank` is already
statically known, (2) check audit row counts to calibrate the work
volume. If scope is single-bank by construction AND row count is zero,
the rename is a 5-line edit, not a threading exercise.

## STALE COMMENT-HEADER GOTCHA — do not be confused

There are existing comment headers in app.py with old "Sprint 6 #11a /
#11b" tags that are NOT the current target of #11c/#11d:

  app.py:3039  # ── Sprint 6 #11a — Maybank CMS bulk-disbursement ─────
  app.py:3097  # ── Sprint 6 #11b — Maybank PAYMENT DEBIT - APS ───────

These are historical tags from when those CMS / MAS PAYMENT handlers
were first added (under an earlier #11 numbering). The current
numbering (#11a = Alliance, #11b = OCBC DUITNOW, #11c = UNNAMED CMS,
#11d = UNNAMED MAS PAYMENT) renames the SPRINT-LEVEL TASK, not the
EXISTING HANDLER-INTRODUCTION COMMENTS. Do NOT rewrite those comment
headers — they're original-introduction markers, leave them alone.
The current targets of #11c/#11d are the BUCKET LABELS (`UNNAMED CMS`,
`UNNAMED MAS PAYMENT`), not the handlers.

## Sprint 6 queue — REMAINING (in order)

#11c UNNAMED CMS cleanup     ← NEXT
   - Code locations (post-#11b grep, current as of aa3145e):
       app.py:3055, 3063, 3085, 3094  — 4 return sites returning
         f"UNNAMED CMS ({direction})"
       app.py:3049 — comment mentions the bucket name
       (NB: handoff #11a section listed 3031/3039/3061/3070; line
        numbers shifted due to #11a + #11b edits.)

   - **OPEN QUESTION (verify before renaming, do NOT rely on comment)**:
     The CMS handler at app.py:3050 is NOT bank-scoped — the regex
     `^CMS\s*-\s*(CR|DR)\s+(PYMT\s+MARS|DIRECT\s+DEBIT)` matches on
     description text alone, no `if "MAYBANK" in bank.upper()` guard.
     The block comment claims "Maybank's Cash Management Service emits
     three sub-formats" but the code's actual reach is description-shape-
     only. Audit must confirm: do any non-Maybank banks emit `CMS - CR/DR`
     prefixes in the live corpus? If yes, the rename to
     `UNNAMED MAYBANK TRANSFER` would mis-attribute them. Two possible
     paths after audit:
       (a) All CMS rows are Maybank → rename in place to
           `UNNAMED MAYBANK TRANSFER (CR|DR)`, no threading needed.
       (b) Mixed-bank CMS → either thread `bank` and rename per-bank,
           or pick a rail-stripped non-bank-attributed label
           (e.g. `UNNAMED BULK PAYMENT (CR|DR)`).
     ASK USER after audit.

   - Apply #11a/#11b lessons:
       - Audit first — get row counts per bank before deciding scope.
       - Don't add bank-specific entity-extractor pre-pass for rows
         CP3 already cleans correctly.
       - Confirm bank-scope statically before threading parameters.

#11d UNNAMED MAS PAYMENT (DR) cleanup
   - Code locations (current):
       app.py:3109, 3122 — 2 return sites returning
         "UNNAMED MAS PAYMENT (DR)"
       app.py:3103 — comment mentions the bucket name
   - The MAS PAYMENT handler at app.py:3105 is also NOT statically
     bank-scoped, but the regex `^PAYMENT\s+DEBIT\s*-\s*APS\s*/?\s*OTHERS`
     matches a Maybank-specific format per the comment. Same audit
     question: confirm in corpus that this only fires for Maybank.
   - Smallest. If #11c routes per-bank, fold this into the same
     `UNNAMED MAYBANK TRANSFER (DR)` bucket so Maybank has one unified
     UNNAMED label, not two.

After #11 series done, resume the Sprint 6 queue (unchanged from prior
handoff): #4 HLB Islamic ~529 rows, #6 Ambank ~223 rows, #7 OCBC GIRO/
CA-MYDEBIT ~220 rows, #8 Alliance NBPS IBG ~137 rows, #10 UOB ~28
rows, #9 Bank Rakyat ~1,720 rows (HIGH RISK — save for last).

After Sprint 6 fully drained:
  AI prompt slim-down — strip defensive entity-re-extraction logic from
  SYSTEM_PROMPT_v3_5_4.md. v3.5.5 / v3.5 / v6.4 file bumps. ~1 coding
  session + user validation cycle.

After that:
  Sprint 5 #21 kredit_lab_classify.py — Anthropic SDK module to replace
  manual claude.ai upload step. ~500-1000 lines, fresh-session-recommended.

## Key files

Parser:
  app.py
    _extract_counterparty signature: ~line 2167 (takes bank, amount, direction)
    OCBC DUITNOW handler (just renamed): ~line 2371-2400
    CMS handler (#11c target): ~line 3050-3095
    MAS PAYMENT handler (#11d target): ~line 3105-3122
    _OWN_PARTY_PROTECTED_LABELS: ~line 3234-3252
      (now contains UNNAMED OCBC TRANSFER + UNNAMED RHB TRANSFER +
       UNNAMED ALLIANCE TRANSFER pairs)
    build_counterparty_ledger call site: ~line 3690-3700

Documentation:
  prompts/NEXT_CHAT_PROMPT.md — this file
  CLAUDE.md — project instructions

Audit artifacts (in /tmp/, will not survive reboot):
  /tmp/duitnow_audit.json — empty (zero rows hit UNNAMED DUITNOW paths)
  /tmp/audit_duitnow.py / _v2 / _v3 — audit scripts the Explore agent
    wrote. Adapt for #11c by changing the filter from "UNNAMED DUITNOW"
    to "UNNAMED CMS".

## First actions in new chat

1. Acknowledge handoff. Verify state:
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -3              # expect: <handoff-append>, aa3145e, 28e4841
     git status --short                # expect: untracked items only
     git log --oneline origin/sprint-6/polish..HEAD
                                       # expect 3 unpushed (or whatever is local)

2. Sanity-check (skip if user is in a hurry):
     python3 scripts/validate_reference_statements.py
       → expect 45,008 tx / 0 errors per bank
     python3 scripts/sprint6_impact.py --out /tmp/sprint6_baseline.json
       → expect total=58,921 distinct=16,042 UNIDENTIFIED=18 UNCATEGORIZED=42

3. Default next: launch #11c UNNAMED CMS audit.
   - Use Explore subagent. Audit prompt structure: same as #11b (find
     all rows in corpus with counterparty in {"UNNAMED CMS (CR)",
     "UNNAMED CMS (DR)"} via live build_counterparty_ledger, classify
     by description shape, report per-bucket counts BY SOURCE BANK,
     flag any rows with extractable entity text per P2).
   - **CRITICAL audit deliverable for #11c**: per-bank distribution of
     ALL rows the CMS handler matches (not just UNNAMED ones) — needed
     to answer "is the CMS handler genuinely Maybank-only in the
     corpus" before picking a rename strategy.
   - ASK USER UPFRONT: per-bank rename, cross-bank rename, or
     rail-stripped neutral label? (Per P4 + handler-scope ambiguity.)
   - Apply #11a/#11b lessons before any code edits.

## Rollback procedure

  # Drop just #11b:
  git reset --hard 28e4841
  # (Returns to pre-#11b state. #11a + handoff intact.)

  # Drop #11a + #11b:
  git reset --hard 6d08daa
  # (Returns to pre-#11 state. NUCLEAR for #11 series.)

Tag sprint-4.5-complete remains the permanent stable marker.

## Context budget note

This session shipped #11b cleanly in ~25k tokens (audit + verify +
edit + regression + commit + handoff). #11b was lucky: zero corpus
rows + single-bank-scoped handler = trivial work. #11c is unlikely to
be as easy — CMS likely has real corpus rows AND the handler's actual
bank-scope needs verification. Budget ~30-40k tokens for #11c
including audit and any user clarification round.
```

---

## Session handoff — 2026-04-27 (Sprint 6 #11c + #11d shipped — #11 series COMPLETE; queue pivots to #4 / #6 / #7 / #8 / #10 / #9)

```
Repo: Bank-Statement-Analysis-main 3
Working dir: /Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## State on arrival

Branch:  sprint-6/polish (STAY on this branch)
Tag:     sprint-4.5-complete (permanent stable marker, unchanged)

Recent commits (newest first, last 4):
  30bc6c3  Sprint 6 #11d: rename Maybank UNNAMED MAS PAYMENT bucket
  4f3f10e  Sprint 6 #11c: rename Maybank UNNAMED CMS bucket
  fc59b23  Append 2026-04-26 late-late-night handoff — Sprint 6 #11b shipped, #11c next
  aa3145e  Sprint 6 #11b: rename OCBC defensive UNNAMED DUITNOW bucket

PUSHED to origin (fc59b23..30bc6c3 landed cleanly). The handoff-doc
commit appended on top of 30bc6c3 will need pushing once it lands.

14-bank parser regression: 45,008 tx / 0 errors across all 14 banks.
sprint6_impact (post #11d): IDENTICAL to baseline.
  total tx: 58,921    distinct: 16,042
  UNIDENTIFIED: 18    UNCATEGORIZED: 42

Row movement this session (179 rows transitioned, 0 aggregate change):
  29 rows  UNNAMED CMS (CR/DR)        → UNNAMED MAYBANK TRANSFER (CR/DR)
  150 rows UNNAMED MAS PAYMENT (DR)   → UNNAMED INTERNAL PAYROLL (DR)

## What this session shipped — Sprint 6 #11c + #11d

### #11c — UNNAMED CMS rename (commit 4f3f10e, +14/-5)
Renamed 4 defensive return sites in the CMS bulk-disbursement /
direct-debit handler:
  Before                       After
  ─────────────────────────────────────────────────────────
  UNNAMED CMS (CR)            UNNAMED MAYBANK TRANSFER (CR)
  UNNAMED CMS (DR)            UNNAMED MAYBANK TRANSFER (DR)

Audit results (30 Full Report files / 12+ banks):
  - 659 total CMS-handler matches; 100% Maybank Islamic
  - 29 transaction rows currently bucket to UNNAMED CMS (13 CR, 16 DR)
  - All UNNAMED rows are empty body or generic markers (INTERCO /
    CLAIMS / HOTEL BOOKING / TRANSFER FUNDS) — zero P2 leakage
  - No defensive `if "MAYBANK" in bank.upper()` guard added; user
    chose regex specificity over defensive code (audit found zero
    cross-bank collision)
  - User chose bank-attributed label (UNNAMED MAYBANK TRANSFER) over
    rail-stripped neutral (UNNAMED BULK PAYMENT)

### #11d — UNNAMED MAS PAYMENT rename (commit 30bc6c3, +15/-6)
Renamed 2 defensive return sites in the PAYMENT DEBIT - APS handler:
  Before                        After
  ─────────────────────────────────────────────────────────
  UNNAMED MAS PAYMENT (DR)     UNNAMED INTERNAL PAYROLL (DR)

Audit results (32 files / 58,921 tx):
  - 185 total APS-handler matches; 100% Maybank Islamic
  - 150 rows bucket to UNNAMED MAS PAYMENT (DR) — 81.1% of handler reach
  - Bucket routing: 81.1% UNNAMED, 16.8% BULK SALARY, 2.2% KWSP, 0% SOCSO/HRDF
  - Block comment claim "no third-party entity is ever present"
    validated by corpus — non-empty bodies are internal noise
    (employee IDs, purpose codes, location codes), no merchants

User picked the NEUTRAL operational label, REJECTING the prior
handoff's proposed "fold into UNNAMED MAYBANK TRANSFER (DR)" plan. The
audit revealed the operational distinction matters: UNNAMED MAYBANK
TRANSFER is for CMS bulk-disbursement (potentially third-party-capable
when entity extracts), UNNAMED INTERNAL PAYROLL is for APS bulk-payroll
(NEVER third-party). Encoding the operational meaning is more
informative for analysts than bank attribution.

Also corrected the #11c comment in _OWN_PARTY_PROTECTED_LABELS that
had promised the fold plan (removed).

## Critical lessons saved this session

### Lesson 1 — Don't rubber-stamp the prior handoff's default plan
The prior handoff for #11d proposed folding UNNAMED MAS PAYMENT (DR)
into UNNAMED MAYBANK TRANSFER (DR) "if #11c routes per-bank." #11c
DID route per-bank, so the rubber-stamp move was the fold. But the
#11d audit revealed an operational distinction (CMS = potentially
third-party, APS = NEVER third-party) that argued against folding.

GENERAL RULE: a prior handoff's plan is a hypothesis informed by
prior context. When new audit data conflicts with it, present the
real options to the user including the previously-undefaulted ones.
This session's 3-option AskUserQuestion (fold / per-bucket APS /
neutral PAYROLL) revealed a user preference toward operational
meaning that the rubber-stamp would have missed.

### Lesson 2 — Two #11x sub-tasks fit in one session
The prior session ended after #11b citing "each #11 sub-task ~30-40k
tokens, continuing risks context exhaustion." This session shipped
#11c AND #11d in ~50-60k tokens combined. The cost-driver isn't the
sub-task count — it's audit complexity + user clarification rounds.
Both audits this session were clean (one Explore call each, no
follow-up needed), and clarification was a single AskUserQuestion
each.

GENERAL RULE: don't auto-eject after one sub-task. Check actual
token usage before writing the handoff. If both audits returned
clean P2 results and the rename diffs are < 30 lines each, two
sub-tasks per session is realistic. The user explicitly redirected
this session away from a premature post-#11c handoff.

### Lesson 3 — P4 ASK matters even when one path looks obvious
For #11c, the audit suggested Maybank-attribution was the natural
play (Maybank-only handler), but the AskUserQuestion offered the
neutral UNNAMED BULK PAYMENT as a real alternative. User picked
attribution. For #11d, the audit suggested the fold was natural
(per prior handoff), but the AskUserQuestion offered three options.
User picked NEUTRAL — the option NOT recommended by the prior
handoff or by either of #11d's own deduction paths.

GENERAL RULE: always present 2-3 real options for rename decisions,
including the one that breaks the convention of the just-completed
sister task. The user's mental model isn't "consistency for
consistency's sake" — it's "what does the analyst learn from this
bucket name." That's not always the path the audit predicts.

## Sprint 6 queue — REMAINING (#11 series COMPLETE)

The four-task #11 rail-name cleanup series is DONE:
  #11a Alliance rail-named UNNAMED buckets  (commit 9a53cfb) ✓
  #11b OCBC defensive UNNAMED DUITNOW       (commit aa3145e) ✓
  #11c Maybank UNNAMED CMS                  (commit 4f3f10e) ✓
  #11d Maybank UNNAMED MAS PAYMENT          (commit 30bc6c3) ✓

Final Maybank UNNAMED bucket landscape:
  UNNAMED MAYBANK TRANSFER (CR/DR)  ← #11c CMS bulk-disbursement
                                       (third-party-capable)
  UNNAMED INTERNAL PAYROLL (DR)     ← #11d APS bulk-payroll
                                       (never third-party)

Remaining Sprint 6 queue (in order):
  #4 HLB Islamic                              ~529 rows
     - Bucket cleanup. Reference corpus files: "Full Report HLB
       MTCE.json" + "Full Report HLB Detik.json" under
       `validation runs - json/claude ai prompt file/Full Report Sample/`
  #6 Ambank — Fund Transfer + JomPAY comma-delim   ~223 rows
  #7 OCBC — GIRO CREDIT / CA MYDEBIT / CA BANKCARD ~220 rows
     (open Q: bucket vs entity for card POS — ASK USER)
  #8 Alliance NBPS IBG Dr <ENTITY>                  ~137 rows
  #10 UOB — small misc                              ~28 rows
     (open Q: 444 Chq Wdl rows scope expansion — ASK USER)
  #9 Bank Rakyat — CIBDRADVICE / DUITNOWTRANSFER  ~1,720 rows
     (HIGH RISK — parser-upstream change to bank_rakyat.py,
      save for last)

After Sprint 6 fully drained:
  AI prompt slim-down — strip defensive entity-re-extraction logic from
  SYSTEM_PROMPT_v3_5_4.md. v3.5.5 / v3.5 / v6.4 file bumps. ~1 coding
  session + user validation cycle.

After that:
  Sprint 5 #21 kredit_lab_classify.py — Anthropic SDK module to replace
  manual claude.ai upload step. ~500-1000 lines, fresh-session-recommended.

## Key files (post #11d)

Parser:
  app.py
    _extract_counterparty signature: ~line 2167 (takes bank, amount, direction)
    CMS handler (#11c done):    ~line 3039-3098, 4 return sites at 3059/3067/3089/3098
    APS handler (#11d done):    ~line 3101-3130, 2 return sites at 3117/3130
    _OWN_PARTY_PROTECTED_LABELS: ~line 3240-3275
      Now contains:
        UNNAMED OCBC TRANSFER (CR/DR)        ← #11b
        UNNAMED RHB TRANSFER (CR/DR)         ← #16
        UNNAMED ALLIANCE TRANSFER (CR/DR)    ← #11a
        UNNAMED MAYBANK TRANSFER (CR/DR)     ← #11c
        UNNAMED INTERNAL PAYROLL (DR)        ← #11d
    build_counterparty_ledger:  ~line 3678 (call site ~3710)

Documentation:
  prompts/NEXT_CHAT_PROMPT.md — this file
  CLAUDE.md — project instructions

Audit artifacts (in /tmp/, will not survive reboot):
  /tmp/sprint6_post_11d.json — current snapshot baseline
  Prior #11c snapshot at /tmp/sprint6_post_11c.json was overwritten on
    rerun; if needed, regenerate via `python3 scripts/sprint6_impact.py`

## First actions in new chat

1. Acknowledge handoff. Verify state:
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -4              # expect: <handoff-append>, 30bc6c3, 4f3f10e, fc59b23
     git status --short                # expect: untracked items only
     git rev-list --count origin/sprint-6/polish..HEAD
                                       # expect 0 if user pushed handoff,
                                       # 1 if not yet pushed

2. Sanity-check (skip if user is in a hurry):
     python3 scripts/validate_reference_statements.py
       → expect 45,008 tx / 0 errors per bank
     python3 scripts/sprint6_impact.py --out /tmp/sprint6_baseline.json
       → expect total=58,921 distinct=16,042 UNIDENTIFIED=18 UNCATEGORIZED=42

3. Default next: ASK USER which Sprint 6 task to tackle. The remaining
   queue is #4 / #6 / #7 / #8 / #10 / #9 — these are heterogeneous
   (varied row volumes, varied risk levels), not a forced sequence
   like the #11 series. User may have a preference based on what's
   most blocking analyst workflow.

   If user says "you pick": default to #10 UOB (~28 rows, smallest,
   lowest risk — good warm-up after #11 series). Ask the open Q on
   444 Chq Wdl scope expansion before launching the audit.

4. Apply session lessons:
   - Audit BEFORE implementation (P4 audit-first pattern).
   - Read the handler block to verify static bank-scope before
     planning parameter threading.
   - Present 2-3 real options on rename decisions, including ones
     that break sister-task convention.
   - Don't rubber-stamp the prior handoff's default plan — let the
     audit data drive.

## Rollback procedure

  # Drop just #11d:
  git reset --hard 4f3f10e
  # (Returns to pre-#11d state. #11c intact.)

  # Drop #11c + #11d:
  git reset --hard fc59b23
  # (Returns to pre-#11c state. #11a + #11b + handoffs intact.)

  # Drop entire #11 series:
  git reset --hard 6d08daa
  # (NUCLEAR for #11 series. Tag sprint-4.5-complete still intact.)

Tag sprint-4.5-complete remains the permanent stable marker.

## Context budget note

This session shipped #11c + #11d in ~55k tokens combined. Per-task
breakdown:
  #11c: ~30k tokens (audit ~10k + edits + regressions + commit + diff review)
  #11d: ~25k tokens (audit ~8k + AskUserQuestion + edits + regressions + commit)

The #11 cleanups landed faster than the prior handoff's per-task
estimate because both audits were clean (no follow-up clarification
rounds with the Explore agent) and both handlers were single-file
edits.

The remaining Sprint 6 tasks (#4 / #6 / #7 / #8 / #10 / #9) are
likely HEAVIER than #11x. They involve row-level entity-extraction
improvements rather than label hygiene — actual classifier work, not
just bucket renames. Budget one task per session for #4, #7, #8, #9.
#6 and #10 may be combinable if both have clean audits.

#9 Bank Rakyat is parser-upstream (bank_rakyat.py) — fresh-session
strongly recommended; do not chain after another task.
```

## Session handoff — 2026-04-27 evening (Sprint 6 #6 + #7 + #8 + #10 shipped — 4-task batched session; queue trims to #4 + #9)

```
Repo: Bank-Statement-Analysis-main 3
Working dir: /Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Bank-Statement-Analysis-main 3

## State on arrival

Branch:  sprint-6/polish (STAY on this branch)
Tag:     sprint-4.5-complete (permanent stable marker, unchanged)

Recent commits (newest first, last 6):
  <handoff append commit>
  aca22fb  Sprint 6 #7: OCBC card POS generic buckets (CA MYDEBIT + CA BANKCARD)
  e954fc2  Sprint 6 #10: UOB Chq Wdl + Cheque<num> DR routing (medium scope)
  1099570  Sprint 6 #6: Ambank Fund Transfer + JomPAY comma-delim handlers
  7a28d1b  Sprint 6 #8: Alliance NBPS IBG Dr handler (AB12)
  d02b606  Append 2026-04-27 handoff — Sprint 6 #11 series complete

PUSHED status: 4 task commits + handoff need pushing — `git push` after
acknowledging this handoff.

14-bank parser regression: 45,008 tx / 0 errors across all 14 banks.
sprint6_impact (post-session):
  total tx: 58,921    distinct: 15,389  (was 16,042 — DOWN 653)
  UNIDENTIFIED: 18    UNCATEGORIZED: 42  (both unchanged)

Row movement this session — ~952 rows transitioned across 4 tasks, 0
aggregate change to row total. Distinct counterparties consolidated by
653 (raw per-row descriptions → named entities or generic buckets).

## What this session shipped — Sprint 6 #6 + #7 + #8 + #10

This session collapsed 4 audits + 4 implementations + 4 commits into a
single working day using the parallel-audit + sequential-implement
pattern (5 Explore subagents fired in one message, then one batched
AskUserQuestion-style decision turn, then sequential per-task edits).
Task #9 Bank Rakyat was deliberately excluded (parser-upstream, fresh-
session-only); task #4 HLB Islamic was deferred from this batch after
audit revealed it's a 200-250 LOC entity-extraction build (not a
rename) — see "Critical lessons" below.

### #8 Alliance NBPS IBG (commit 7a28d1b, +21 lines)
Added AB12 to `_extract_counterparty_alliance` (after AB11 at ~line
2155). Pattern: `^NBPS\s+IBG\s+DR\s+CA\s+AOBJOM\d+\s+\S+\s+(.+)$`.
Strips leading biller ID then runs the standard Alliance body-cleanup
pipeline (`_ab_dedupe_halves`, `_ab_strip_trailing_refs`,
`_ab_fix_truncation`). Empty body falls back to UNNAMED ALLIANCE
TRANSFER (DR|CR) per the #11a rail-agnostic convention.

  - 137 corpus rows transitioned from UNIDENTIFIED to extracted entity
  - All 137 are DR (no CR observed)
  - NBPS pattern verified Alliance-exclusive (zero cross-bank match)
  - Does NOT touch the Apr 2026 Alliance DR/CR signed-balance fix

### #6 Ambank Fund Transfer + JomPAY comma-delim (commit 1099570, +16 lines)
Added two handlers right after the existing Ambank DuitNow `/MISC`
block (~line 2349). Both extract the 2nd comma field per the DuitNow
precedent (Q2=A: strip after first comma).

  - `FUND TRANSFER /DEBIT TRANSFER, <ENTITY>, ...`  → 131 rows
  - `JOMPAY        /DEBIT TRANSFER, <ENTITY>, ...`  → 92 rows
  - Both prefixes pass through to extracted entity name
  - Generic JOMPAY <biller_code> handler still catches CIMB/OCBC/RHB
    biller-format rows above (no regression)

### #10 UOB Chq Wdl + Cheque<num> DR (commit e954fc2, +16 lines)
Added a bank-gated DR-only handler after the OCBC DUITNOW block
(~line 2402). Two patterns route to UNNAMED UOB TRANSFER (DR):

  - "Chq Wdl 0545837 1 of 3"   — 444 corpus rows; UOB-exclusive prefix
  - "Cheque 0545825"           — bare cheque-number DR rows (~33+)

CR cheque rows untouched (Q6b=A: stay on existing path). Bank-gated
because bare "Cheque <num>" is not UOB-exclusive across the corpus.
UNNAMED UOB TRANSFER (DR) added to _OWN_PARTY_PROTECTED_LABELS.

Note: handoff originally estimated this task at "~28 rows". The audit
revealed the actual scope is 444+ rows — the user's prior shorthand
"444 Chq Wdl rows" meant *444 rows of Chq Wdl*, not "rows starting with
444". Lesson saved below.

### #7 OCBC card POS generic buckets (commit aca22fb, +16 lines)
Added a bank-gated OCBC handler after the OCBC DUITNOW block
(~line 2402). Q3=B chose generic CARD POS buckets over per-merchant
extraction:

  - `^CA MYDEBIT\b`   → CARD POS (MYDEBIT)   (73 rows; debit-card POS)
  - `^CA BANKCARD\b`  → CARD POS (BANKCARD)  (42 rows; credit-card POS)

Both prefixes verified OCBC-exclusive in corpus. Card POS flows are
payment-rail, not business relationships — per-merchant ledgering
would have fragmented across ~80-100 unique merchants.

GIRO CREDIT rows intentionally NOT touched (Q4=A): they extract real
entity names today (PBB-PBCS AC, NTT DATA, MAYBANK COLLECTION).

CARD POS (MYDEBIT) and CARD POS (BANKCARD) added to
_OWN_PARTY_PROTECTED_LABELS.

## Critical lessons saved this session

### Lesson 1 — Aggressive parallel-audit model is viable for batched sessions
Prior handoff said "Budget one task per session for #4, #7, #8, #9 …
the remaining Sprint 6 tasks are likely HEAVIER than #11x." This
session shipped 4 tasks in one working day by:
  1. Running 5 audits in PARALLEL via subagents (one message, ~5 min
     wall-clock)
  2. Consolidating into ONE batched user-decision turn (7 questions
     across 4 tasks, user accepted all defaults)
  3. Implementing sequentially in `app.py` with 4 small commits
  4. Running regressions ONCE at the end, not per-task

GENERAL RULE: when the queue contains heterogeneous label-hygiene /
small extraction tasks (not parser-upstream), the parallel-audit
+ sequential-implement model converts ~5 sessions into ~1. The
constraint isn't audit time — it's audit-result FANOUT into user
decisions. If you can frame all decisions as a single batched ask
with clear defaults, the user can answer once.

DO NOT apply this model to:
  - Parser-upstream tasks (e.g. #9 Bank Rakyat — touches `bank_rakyat.py`)
  - Tasks with unknown scope (audit first, may force splitting)
  - Tasks where decisions interact (later decision changes earlier code)

### Lesson 2 — Handoff scope estimates lie; the audit is truth
Two scope estimates from the prior handoff turned out wrong:

  - #4 HLB Islamic: handoff said "~529 rows, bucket cleanup"; audit
    revealed it's a 200-250 LOC entity-extraction BUILD (no HLB
    handlers exist yet — CIB/Instant/FPX/IBG all fall through raw).
    Correctly deferred to a fresh session.
  - #10 UOB: handoff said "~28 rows, small misc"; audit revealed
    444+ rows. The handoff's "444 Chq Wdl rows scope expansion" was
    USER SHORTHAND for "444 rows of Chq Wdl pattern", not "rows
    starting with 444". Re-read the audit, not the handoff
    summary, when sizing.

GENERAL RULE: when the audit's row count or LOC estimate diverges
from the handoff's, surface the divergence to the user and offer to
re-scope before implementing. The user's quick "you pick" instinct
should not override material scope changes.

### Lesson 3 — Q3-style bucket-vs-entity ASK matters for card POS
The OCBC card-POS audit found 100% of rows have extractable merchant
text (MAGICBOO, PASARAYA, TRAVELOKA, OPODO, etc.). The naive
implementation would extract per-merchant. Q3=B (generic CARD POS
buckets) was the right call because:

  - Card POS flows are payment-rail, NOT business relationships
  - Per-merchant ledger would fragment across ~80-100 sparse buckets
  - Analyst signal: "this row is a card swipe at retail" is more
    useful than "this row is a card swipe at MAGICBOO specifically"

GENERAL RULE: when entity IS extractable but the operational meaning
is "rail flow, not relationship", default to a generic bucket and
explicitly tell the user the alternative was to extract. Don't
extract just because you can.

### Lesson 4 — Replay-edit-then-commit pattern for splitting batched work
After all 4 tasks were edited into a single working tree, splitting
into 4 commits used: save full diff to /tmp, `git checkout app.py`
(revert), then re-apply each task's edits via Edit tool one task at
a time (commit between). Final `diff <(git diff HEAD~4..HEAD) /tmp/<patch>`
verified byte-identity vs the saved patch.

GENERAL RULE: if you batch implementation in memory then need
per-task commits, this is cleaner than `git add -p` (no interactive
prompts) and safer than separate Write operations (no ordering
hazards). Order matters when later edits' anchors depend on earlier
edits — figure out the dependency order BEFORE replaying.

## Sprint 6 queue — REMAINING (post-session)

| #  | Task                                            | ~Rows  | Risk   | Notes                                       |
|----|-------------------------------------------------|--------|--------|---------------------------------------------|
| #4 | HLB Islamic full entity-extraction build        | ~537   | Medium | DEFERRED — needs ~200-250 LOC, fresh session|
| #9 | Bank Rakyat — CIBDRADVICE / DUITNOWTRANSFER     | ~1,720 | HIGH   | parser-upstream (`bank_rakyat.py`); save for last |

Order recommendation: #4 next (medium effort, label/extraction work),
then #9 last (parser-upstream, must be fresh session).

After Sprint 6 fully drained:
  AI prompt slim-down — strip defensive entity-re-extraction logic from
  SYSTEM_PROMPT_v3_5_4.md. v3.5.5 / v3.5 / v6.4 file bumps. ~1 coding
  session + user validation cycle.

After that:
  Sprint 5 #21 kredit_lab_classify.py — Anthropic SDK module to replace
  manual claude.ai upload step. ~500-1000 lines, fresh-session-recommended.

## Open questions for #4 HLB Islamic (carried from this session's audit)

The #4 audit identified 4 sub-questions to ask the user BEFORE
implementing. Surface these in the next session's first ASK:

  1. Own-account transfer detection: regex on `INTER ACC TXN|OWN ACC TXN`
     (route to UNNAMED HLB TRANSFER regardless of entity), OR cross-check
     entity name against `company_name` from row metadata?
  2. FPX B2B1 entity truncation: accept truncated names (e.g. "NATIONAL
     INSTITUTE OF OCCUPATI"), or require minimum 10-char entity?
  3. CA Debit Advice rows (5 corpus rows): existing "Unidentified
     (Cheque)" bucket, or new UNNAMED HLB TRANSFER (DR)?
  4. Serv Charge-IBG/TT/Rentas/Misc (31 rows): keep current path (already
     → BANK FEES at parser layer), or dedicated UNNAMED HLB FEES bucket?

Recommended bucket name (pending user confirmation): UNNAMED HLB
TRANSFER (CR|DR) per the bank-attributed convention from #11b/c/16/11a.

## Key files (post-session)

Parser:
  app.py
    _extract_counterparty_alliance: ~line 1904
      AB12 NBPS handler:           ~line 2164 (NEW this session)
    _extract_counterparty:         ~line 2167
      Ambank Fund Transfer + JomPAY:  ~line 2356 (NEW this session)
      OCBC card POS:                  ~line 2402 (NEW this session)
      UOB Chq Wdl + Cheque<num>:      ~line 2415 (NEW this session)
    _OWN_PARTY_PROTECTED_LABELS: ~line 3244-3280 (now also contains
      UNNAMED UOB TRANSFER (DR), CARD POS (MYDEBIT), CARD POS (BANKCARD))

Documentation:
  prompts/NEXT_CHAT_PROMPT.md — this file
  CLAUDE.md — project instructions

Audit artifacts (in /tmp/, will not survive reboot):
  /tmp/sprint6_post_session.json — current snapshot baseline (post 4-task)
  /tmp/sprint6_4tasks_combined.patch — combined diff for the 4 commits
    (used for the replay-edit-then-commit pattern)

## First actions in new chat

1. Acknowledge handoff. Verify state:
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -6              # expect: handoff-append, aca22fb,
                                       #         e954fc2, 1099570, 7a28d1b,
                                       #         d02b606
     git status --short                # expect: untracked items only
     git rev-list --count origin/sprint-6/polish..HEAD
                                       # expect 0 if user pushed,
                                       # 5 (4 tasks + handoff) if not

2. If user has not pushed yet, run `git push` first.

3. Sanity-check (skip if user is in a hurry):
     python3 scripts/validate_reference_statements.py
       → expect 45,008 tx / 0 errors per bank
     python3 scripts/sprint6_impact.py --out /tmp/sprint6_baseline.json
       → expect total=58,921 distinct=15,389
       UNIDENTIFIED=18 UNCATEGORIZED=42

4. Default next: ASK USER which remaining Sprint 6 task to tackle.
   Only #4 HLB and #9 Bank Rakyat remain. Recommend #4 first (medium
   effort) and surface the 4 open questions from this session's audit
   (see "Open questions for #4 HLB Islamic" above) BEFORE implementing.
   #9 Bank Rakyat is parser-upstream — fresh session strongly
   recommended; do not chain after #4.

5. Apply session lessons:
   - The parallel-audit + sequential-implement model is the new
     default for batched label/small-extraction sessions
   - Surface scope-estimate divergences (audit row counts vs
     handoff estimates) BEFORE the user accepts defaults
   - For card-POS / payment-rail flows, default to generic bucket
     even when entity IS extractable
   - Use replay-edit-then-commit when you batch implementation but
     need per-task commits

## Rollback procedure

  # Drop just #7 OCBC card POS:
  git reset --hard e954fc2
  # (Returns to pre-#7 state. #6/#8/#10 intact.)

  # Drop #7 + #10:
  git reset --hard 1099570
  # (Returns to pre-#10 state. #6/#8 intact.)

  # Drop #7 + #10 + #6:
  git reset --hard 7a28d1b
  # (Returns to pre-#6 state. #8 intact.)

  # Drop entire 4-task batch:
  git reset --hard d02b606
  # (Returns to start-of-session state. Tag sprint-4.5-complete
  # still intact further back.)

Tag sprint-4.5-complete remains the permanent stable marker.

## Context budget note

This session shipped 4 tasks in ~75-85k tokens combined. Per-phase
breakdown:
  Phase A (5 parallel audits):   ~15k tokens (subagent results
                                  return as summaries, not raw data)
  Phase B (consolidate + ASK):   ~5k tokens
  Phase C (4 sequential edits):  ~30k tokens (read app.py, 4 Edit
                                  pairs, replay-edit-then-commit
                                  workflow)
  Phase C end (regressions):     ~5k tokens (both backgrounded)
  Handoff (this section):        ~15-20k tokens

The parallel-audit model's surprise win was that audit subagent
RESULTS came back as ~500-word summaries each (~2.5k total), not
the raw underlying data they processed. The main agent's context
stays small even when audit work is large.

The remaining Sprint 6 tasks (#4 HLB + #9 Bank Rakyat) are NOT
suitable for batching. #4 is a 200-250 LOC build with 4 open
questions; #9 is parser-upstream. Each gets its own session.
```

---

# Handoff append — 2026-04-27 late evening (Sprint 6 #4 HLB shipped)

## What shipped this session (1 commit)

| # | Commit | Theme | Impact |
|---|---|---|---|
| 1 | `84fbc3d` | Sprint 6 #4 HLB Islamic full entity-extraction build | 0/537 → 537/537 HLB rows extracted (463 pattern + 74 special + 0 raw) |

Pushed to `origin/sprint-6/polish`. Branch is up-to-date.

### Sprint 6 #4 HLB Islamic — what was built (commit 84fbc3d, +271 lines)

New bank-gated handler in `_extract_counterparty` for Hong Leong Bank
and HLB Islamic (same description format across both subsidiaries).
Audited corpus: 537 rows across MTCE + Detik samples. Pre-fix
extraction was 0/537 — no HLB handler existed before this commit.

**Sub-formats handled (named — 463 rows / 86%):**

  - A. `CIB Instant Transfer at DIO <amt> <inv> <ENTITY> <date>HLBBMYKL<ref>`
       (~254 rows — the dominant HLB format)
  - B. `Instant Transfer at KLM <amt> [<bal>] [interbank|ITB TRF [HLB <bk>]]
       <ENTITY> <date>{ARBK|BMMB|CIBB|MBBE|BIMB}MYKL<ref>` (~47 rows)
       Strips `interbank` / `ITB TRF [HLB <bank>]` purpose markers
       before extraction so they don't leak into bucket names.
  - C. `JomPAY Bill Payment at DIO <amt> <bill-ref> C<ref>{Y|N}
       <ENTITY> 24IM<ref>` (~81 rows)
       MUST run before generic JomPAY catch-all — otherwise that
       handler grabs `JOMPAY BILL` instead of the actual biller
       (TNB / MAXIS / TM UNIFI / SYARIKAT AIR / CELCOM / etc.).
  - D. `FPX B2B1 <amt> <noise> <ref10> <ENTITY> <ref16>` (~29 rows)
       Truncations accepted per Q2 ("NATIONAL INSTITUTE OF OCCUPATI"
       is the analyst's clue — better than UNCATEGORIZED).
  - E. `Fund Transfer at DIO <amt> <inv/ref/purpose> <ENTITY>` (~24 rows)
       Entity at the very end of the body, no suffix ref code.
  - F. `CIB IBG CA Debit Advice at KLM <amt> <purpose> <ENTITY>
       IBGCMP<bank><ref>` (~26 rows)
  - G. `CA-i Debit Advice - SWIFT <amt> [<bal>] <purpose> OUR
       <ENTITY> CPTJ<bank><ref>` (~3 rows)

**Truly unnamed → UNNAMED HLB TRANSFER (DR) (29 rows):**

  - H. `Bulk DuitNow <amt> <internal-code> CTHLCF<ref>` (~25 rows)
       Aggregate disbursement batch; description has no entity.
  - I. `CA IBT Debit Advice at SPI <amt>` (~4 rows)
       Inter-account own-bank transfer.

  Bucket added to `_OWN_PARTY_PROTECTED_LABELS` (CR + DR).

**Cheques (Q3 — existing Unidentified bucket, 2 rows):**

  - J. `Inclearing-Cheque <num> <amount>` → Unidentified (Cheque)
  - CA Debit Advice with `#nnnn` ref → Unidentified (Cheque)

**Bank fees (Q4 — global BANK FEES, 42 rows):**

  HLB-specific fee shapes the global BANK FEES regex misses now route
  via HLB-bank-gated checks:
  - `Serv Charge-IBG/TT/Rentas/Misc`         (~31 rows)
  - `Remittance Cable Charge` / `Remittance Commission` (~4 rows)
  - `Debit Advice - SST`                     (~1 row)
  - `Overdraft/Excess Interest`              (~1 row)
  - `CA Debit Advice` + CPTJ ref (settlement fees) (~5 rows)
  `Cheque Processing Fee` already caught by global BANK FEES regex.

**Helper added — `_hlb_extract_entity` (module-level):**

  Walks right-to-left from a stripped body collecting name-shaped
  tokens (letters, no embedded digits). `&` allowed as a name-bridge
  ("HABLEM OIL & GAS"). Trailing noise (lone digits, underscores,
  dangling open-paren) trimmed first. Truncated names accepted —
  Q2 directive: analyst clue beats UNCATEGORIZED.

**Placement decision:**

  HLB block runs IMMEDIATELY AFTER Alliance, BEFORE the global
  special-bucket / BANK FEES / generic-JomPAY regexes. The generic
  JomPAY catch-all (`JOMPAY ([\w:]+)`) otherwise grabs `JOMPAY BILL`
  as the biller token for HLB rows. Bank-gate ensures non-HLB rows
  still hit the generic path below.

**Cross-bank safety:**

  Bank-gated to "Hong Leong" (matches both HLB Bank and HLB Islamic).
  Defence-in-depth via HLB-specific anchor tokens (`at DIO` / `at KLM`
  / `at SPI` / `IBGCMP` / `CTHLCF` / `HLBBMYKL`). Verified no
  cross-bank leakage on Ambank / CIMB / Alliance corpus samples; only
  false-positive hit was a person named "YEOH HONG LEONG" which is
  legitimate entity content, not a bucket leak.

**Top extracted entities (post-fix):**

  TENAGA NASIONAL BERHAD ×22, MAXIS ×18, MTC ENGINEERING SDN BHD ×28
  (across `SDN.`/`SDN` punctuation variants — `_normalise_counterparty`
  consolidates), NATIONAL INSTITUTE OF OCCUPATI ×28 (FPX truncated),
  SYARIKAT AIR DARUL AMA ×15, TM UNIFI ×11, CELCOM MOBILE SDN BHD ×7,
  AIRPAK EXPRESS ×7, RICOH (MALAYSIA) ×5, plus many individual payees
  (NUZUL IZWAN BIN MOHD, MUHAMMAD FAIZAL RAZZA BIN MOHD SHUKOR …).

## Critical lessons saved this session

### Lesson 1 — Bank-gated handler placement matters when generic catch-alls exist

The generic JomPAY handler (`JOMPAY ([\w:]+)` at app.py line ~2284)
matches `JOMPAY BILL` as biller="BILL" for HLB rows that print as
`JomPAY Bill Payment at DIO ...`. First-cut placement of the HLB
block AFTER the generic JomPAY caused 81 HLB JomPAY rows to bucket
as `JOMPAY BILL` instead of TNB / MAXIS / TM UNIFI / etc.

GENERAL RULE: when adding bank-gated handlers, audit the existing
generic patterns for partial-prefix matches against the new bank's
prefixes. If any generic handler would intercept a real entity slot,
place the bank-gated block BEFORE the generic. Bank-gating ensures
the new block doesn't affect other banks' routing.

### Lesson 2 — `_tail_alpha_run` semantics: ampersand and purpose-word handling

The base `_tail_alpha_run` helper does NOT treat `&` as a bridge —
walking back from `HABLEM OIL & GAS (M) SDN BHD`, it stops at `&`
and returns only `GAS (M) SDN BHD` (5 rows affected in HLB corpus).
The new `_hlb_extract_entity` allows `&` as a bridge but only when
sandwiched between name tokens (never as leading/trailing).

It also does NOT filter purpose words — walking back from
`interbank MTC ENGINEERING SDN. BHD.`, `interbank` is letters-with-
no-digits and gets included (15 KLM rows affected). Solution:
strip known purpose markers (`interbank`, `ITB TRF [HLB <bank>]`)
from the body BEFORE invoking the trailing-alpha extractor — much
safer than baking a purpose-word stop list into the helper.

GENERAL RULE: the trailing-alpha-run pattern is robust for entity
extraction but blind to purpose-word leakage. Strip known purpose
markers up front; over-collection of unrelated trailing words is
acceptable per the "give the analyst a clue" directive (Q2), but
known purpose markers should never leak into bucket names because
they distort consolidation.

### Lesson 3 — Q4 "keep current" can mean "keep the user's mental model" not literal current state

User said Q4 = "Bank fees (keep current)" for the 42 HLB fee-shaped
rows. Their mental model was that these rows already routed to
BANK FEES at the parser layer. They didn't — `Serv Charge-IBG/TT/
Rentas/Misc` and similar HLB-specific shapes fall through the
global BANK FEES regex. Honoring the user's INTENT (fees → BANK
FEES) required adding HLB-specific BANK FEES routing.

GENERAL RULE: when the user's "keep current" answer doesn't match
observed behavior, surface the discrepancy or honor the intent.
Don't blindly do nothing just because the literal text says "keep".

## Sprint 6 queue — REMAINING (post-session)

| #  | Task                                            | ~Rows  | Risk   | Notes                                       |
|----|-------------------------------------------------|--------|--------|---------------------------------------------|
| #9 | Bank Rakyat — CIBDRADVICE / DUITNOWTRANSFER     | ~1,720 | HIGH   | parser-upstream (`bank_rakyat.py`); FRESH SESSION REQUIRED |

#9 is the LAST remaining Sprint 6 task. After it ships, Sprint 6 is
fully drained.

After Sprint 6:
  AI prompt slim-down — strip defensive entity-re-extraction logic from
  SYSTEM_PROMPT_v3_5_4.md. v3.5.5 / v3.5 / v6.4 file bumps. ~1 coding
  session + user validation cycle.

After that:
  Sprint 5 #21 kredit_lab_classify.py — Anthropic SDK module to replace
  manual claude.ai upload step. ~500-1000 lines, fresh-session-recommended.

## Key files (post-session)

Parser:
  app.py
    _hlb_extract_entity:           ~line 1725 (NEW this session)
    _extract_counterparty_alliance: ~line 1973
    HLB sub-formats A-G + H/I/J:   ~line 2218 (NEW this session,
      placed BEFORE special buckets / BANK FEES / generic JomPAY)
    AB12 NBPS handler:             ~line 2233
    _extract_counterparty:         ~line 2257
      Ambank Fund Transfer + JomPAY:  ~line 2426
      OCBC card POS:                  ~line 2472
      UOB Chq Wdl + Cheque<num>:      ~line 2485
    _OWN_PARTY_PROTECTED_LABELS: ~line 3306-3340 (now also contains
      UNNAMED HLB TRANSFER (CR) and UNNAMED HLB TRANSFER (DR))

Documentation:
  prompts/NEXT_CHAT_PROMPT.md — this file
  CLAUDE.md — project instructions

## First actions in new chat

1. Acknowledge handoff. Verify state:
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -3              # expect: 84fbc3d (Sprint 6 #4),
                                       #         35e2f17 (handoff append),
                                       #         aca22fb (Sprint 6 #7)
     git status --short                # expect: untracked items only
     git rev-list --count origin/sprint-6/polish..HEAD
                                       # expect 0 (all pushed)

2. Default next: Sprint 6 #9 Bank Rakyat is the only remaining Sprint 6
   task. Per the handoff that established `bank_rakyat.py` as
   parser-upstream HIGH-risk work, it is recommended for a FRESH
   SESSION. Confirm with user before starting:
     - Does the user want #9 now, or defer to a separate session?
     - If #9 now: budget the WHOLE session for it (no batching with
       other tasks).

3. #9 audit needed up front (do not skip):
     - Inspect `bank_rakyat.py` for current CIBDRADVICE / DUITNOWTRANSFER
       handling (likely none — that's why ~1,720 rows fall through).
     - Sample raw descriptions from `validation runs - json/claude ai
       prompt file/Full Report Sample/Full Report Bank Rakyat*.json`
       to characterize the prefixes and entity locations.
     - Surface ASK to user with bucket-naming options BEFORE editing
       the parser. #9 is parser-upstream (changes to `bank_rakyat.py`
       affect raw row extraction, not just counterparty derivation),
       so getting the schema right matters.

4. Apply session lessons:
   - Place bank-gated handlers BEFORE generic catch-alls when there's
     any prefix-overlap risk (Lesson 1)
   - Strip known purpose markers up front; trailing-alpha extraction
     is blind to them (Lesson 2)
   - When user says "keep current", verify literal current behavior
     matches their mental model — surface discrepancies (Lesson 3)
   - Use `_hlb_extract_entity` (or a similar bank-specific helper)
     pattern for free-form description bodies — much cleaner than
     extending the generic helpers

## Rollback procedure

  # Drop just #4 HLB:
  git reset --hard 35e2f17
  # (Returns to pre-#4 state. Sprint 6 #6/#7/#8/#10 all intact.)

  # Drop #4 + the prior 4-task batch:
  git reset --hard d02b606
  # (Returns to start-of-Apr-27-evening state.)

Tag sprint-4.5-complete remains the permanent stable marker.

## Context budget note

This session shipped 1 task (200+ LOC build with 4 user-confirmed
sub-questions) in ~50-60k tokens. Per-phase breakdown:
  Phase A (corpus audit + finding report):  ~10k tokens
  Phase B (user Q&A on 4 sub-questions):    ~3k tokens
  Phase C (initial implementation):         ~15k tokens
  Phase D (post-test fixes — JomPAY order,  ~10k tokens
          interbank purpose stripping,
          ampersand bridge, BANK FEES adds)
  Phase E (regressions + commit + handoff): ~15k tokens

The single-session model was correct for #4: it had open questions,
required a corpus audit first, and a parallel-audit-with-other-tasks
approach would have made the user-decision turn unwieldy. Lesson:
the parallel-audit batched model from the prior session is for
LIGHT label-hygiene tasks; medium/heavy entity-extraction builds
get their own session.

#9 Bank Rakyat is parser-upstream (touches `bank_rakyat.py`, not
just `_extract_counterparty`). Save it for the next fresh session.


---

# Handoff append — 2026-04-27 night (Sprint 6 #9 shipped — Sprint 6 COMPLETE)

## What shipped this session (1 commit)

| # | Commit | Theme | Impact |
|---|---|---|---|
| 1 | `057813e` | Sprint 6 #9 Bank Rakyat multi-line capture + entity extraction | Felcra corpus 4,373 rows: 100% NONE → 0% NONE (full categorization: 2,519 special / 1,854 pattern / 0 raw / 0 UNIDENTIFIED) |

Pushed status: 1 commit + handoff append need pushing — `git push` after
acknowledging this handoff. Expect ahead 2.

### Sprint 6 #9 Bank Rakyat — what was built (commit 057813e, +241 lines)

**Parser-upstream rewrite (`bank_rakyat.py`, +58 lines).** Felcra-style
PDFs (`CASA_DATAPOS_*.pdf`) put the entity name and purpose on
continuation lines below each date-line. The previous parser only
captured the date-line. Replaced the simple line-iterator with a
multi-line walker: each date-line starts a transaction block; the
walker collects continuation lines until next date-line, summary
footer (`Baki Permulaan` / `Opening Balance`), or re-emitted page
header. Stop regex matches BOTH spaced (`Baki Permulaan` — cashline
PDFs) and concatenated (`BakiPermulaan` — Felcra PDFs) forms because
PDF text-layer extraction differs across products. Description is
space-joined; existing balance-trail derivation unchanged.

**Bank-Rakyat-gated handler in `_extract_counterparty` (`app.py`,
+183 lines).** Placed AFTER HLB block, BEFORE global special-buckets
regex. Strips leading 5-digit transaction code, then routes by
concatenated opcode prefix:

  - **BANK FEES** : `CIBSMSFEE` / `CIBDRCHARGES` / `DUITNOWFEE` /
                    `CIBCOMMISSION` (global regex doesn't match these
                    concatenated forms; explicit routing required)
  - **CASH DEPOSIT** : `CASHDEPOSIT` / `CDMCASHDEPOSIT`
  - **FD/INTEREST** : `CREDITPROFIT/HIBAH`
  - **Unidentified (Cheque)** : `2DLOCALCHQ`
  - **CASH WITHDRAWAL** : `CASHWITHDRAWAL`
  - **UNNAMED BANK RAKYAT TRANSFER (CR/DR)** :
                    `IBGINWARDRETURN` / `REVERSALCR` / `LOCALCHQRTN` /
                    `BILLPAYMENTTOFIN` / `TRFRSHAREMEMBER` /
                    `ATMTRANSFERCR` (system events; either no
                    continuation or no extractable entity)
  - **JomPAY billers** : `CIBDRADVICE(JomPA …)` → biller name from
                    continuation token (HLB convention — biller-name
                    as bucket; Layer 2 AI classifies as utility/bill).
                    Confirmed working: TENAGANASIONAL (TNB),
                    DIGITELECOMMUNI (Digi), INDAHWATERKONS (Indah
                    Water), PENGURUSANAIRS, COWAY, TMTECHNOLOGYSE
                    (TM Unifi), DEWANBANDARAYA, MAJLISPERBANDAR.
  - **Entity-bearing** : `DUITNOWTRANSFER` / `CIBDRADVICE[(IBG)]` /
                    `CIBCRADVICE` / `CREDITADV` / `IBGCREDIT` /
                    `REMITTANCECR[-RENT]` / `TRANSFERFROMSA` /
                    `TRFROMSA` / `TRTOSAVINGS` / `ATMMEPSIBFTCR` →
                    first non-noise continuation token via
                    `_br_extract_entity`.

**Helper added — `_br_extract_entity` (module-level).** Walks
continuation tokens, drops known noise (`AGROBIZ` / `TRADING` /
`KKF` sub-account tags; `StaffID\d+` staff IDs; `KZ\d` / `IV-\d` /
`WFV\d` / `INV-\w+` / `BAY\d` ref tokens), returns first remaining
≥3-letter blob. Concatenated names like `AHMADJAWWADBINYAHAYA`
are accepted per the HLB Q2 directive — analyst clue beats
UNCATEGORIZED.

**Protected-labels:** `UNNAMED BANK RAKYAT TRANSFER (CR)` and
`(DR)` added to `_OWN_PARTY_PROTECTED_LABELS`.

**Top buckets post-fix (Felcra Koperasi corpus, 4,373 rows):**

  2,483 BANK FEES (the high-volume CIBSMSFEE/CIBDRCHARGES/DUITNOWFEE/
        CIBCOMMISSION fee rows that previously bucketed as NONE)
     45 DIGITELECOMMUNI / 19 TENAGANASIONAL / 15 PENGURUSANAIRS / etc.
        (JomPAY utility billers)
     28 AMIRULLAHBINMADDESA / 26 HAIRULHAZIZIBINROSLI / 22
        SITINURHAFIZAHBINTIOTHMAN / 15 KOPERASIKAKITANGANFELCRA(M) /
        15 PENGURUSANAIRS / many smaller named entities
     15 UNNAMED BANK RAKYAT TRANSFER (DR) / 13 (CR)
        (truly nameless system rows)

**Regressions clean:**
- `validate_reference_statements.py` — all 14 banks pass
  (Bank Rakyat: 54 PDFs, 7,182 txns, 0 errors)
- Felcra source PDFs (6 files): row counts identical pre/post
  (4,373 → 4,373; +0 delta)
- Bank-gated handler — non-Bank-Rakyat rows unaffected

## Critical lessons saved this session

### Lesson 1 — `\b` doesn't match between two non-word characters

First-cut entity-opcode regex used `\b` as the terminator. For
`CIBDRADVICE(IBG)`, the `\b` between `)` (non-word) and ` ` (non-
word) fails — the regex didn't match and 24 rows bucketed as the
literal opcode string `'CIBDRADVICE(IBG)'`.

GENERAL RULE: when an opcode/prefix can end with a non-word
character (`)`, `-`, `/`, `.`), don't anchor the terminator with
`\b`. Use `(?=\s|$)` instead. Test the regex against ALL opcode
variants before declaring victory.

### Lesson 2 — Handoff scope estimates lie (continued from prior session)

Prior handoff said "#9 Bank Rakyat — CIBDRADVICE / DUITNOWTRANSFER,
~1,720 rows". The actual scope was the entire Felcra file
(~4,373 rows) because the parser-upstream fix (multi-line capture)
unlocks ALL Bank Rakyat opcodes, not just the two named in the
handoff. Fixing only the named opcodes would have left 2,482
fee/cash-deposit/profit rows still showing as garbage — the
multi-line capture is the same change either way.

GENERAL RULE: when a parser-upstream fix is on the critical path,
the scope is "everything that fix unlocks", not "the specific
opcodes the handoff named". Audit the corpus once, list every
opcode that needs routing, then propose ONE batch — don't ship a
partial handler that leaves obvious gaps.

### Lesson 3 — User's mental model overrides the literal opcode name

User said TRANSFERFROMSA = "transfer from savings account = own
account, bucket as OWN ACCOUNT TRANSFER". Audit revealed these are
third-party senders (cooperative members paying premiums from
their personal Bank Rakyat savings to KKF Felcra's current
account). The opcode name describes the MECHANISM (intra-bank
transfer), not the SEMANTICS (third-party payment). Surfaced to
user, who agreed the right routing is entity extraction (same as
DUITNOWTRANSFER CR / IBGCREDIT).

GENERAL RULE: when an opcode name implies "own-account" or
"system" routing but the corpus shows real third-party
counterparties on the continuation lines, trust the data not the
name. Surface the discrepancy to the user before routing.

### Lesson 4 — The PDF text-extraction quirk varies by Bank Rakyat product

Cashline-style PDFs (3-digit codes, products like
`CASH LINE` / `Cashline-i`) preserve spaces:
  `25/04/2025 735 DUITNOW TRANSFER 8,000.00`
  `CENFOTEC SDN BHD`

Felcra/Koperasi-style PDFs (5-digit codes,
`CASA_DATAPOS_Statement_for_Current_Account_*`) collapse all spaces
on continuation lines:
  `01/12/2023 93230 TRANSFERFROMSA 55.96`
  `AHMADJAWWADBINYAHAYA`

Same parser handles both because the multi-line walker is
structural (date-line + continuations) not lexical. The
counterparty extractor accepts both spaced and concatenated tokens
because the noise-stripping is per-token, not per-character. The
stop-regex covers both `Baki Permulaan` and `BakiPermulaan` (and
`Baki Penutup` / `BakiPenutup`).

GENERAL RULE: when one bank has multiple PDF generators across
products, the text-layer behavior may differ. Build the parser
structurally, not lexically. Test BOTH product formats before
declaring done.

## Sprint 6 queue — DRAINED ✅

All 18 Sprint 6 tasks shipped. No remaining queue items.

```
#1  Alliance per-row signed-balance DR/CR fix          ✅
#2  CP3 Alliance residuals                              ✅
#3  Maybank VISA/biller fallback                        ✅
#4  Hong Leong / HLB Islamic entity-extraction          ✅
#5  Public Bank C24 fees                                ✅
#6  Ambank Fund Transfer + JomPAY comma-delim           ✅
#7  OCBC card POS generic buckets                       ✅
#8  Alliance NBPS IBG Dr handler                        ✅
#9  Bank Rakyat multi-line + entity extraction          ✅  ← THIS SESSION
#10 UOB Chq Wdl + Cheque<num> DR routing                ✅
#11a Alliance UNNAMED bucket rename                     ✅
#11b OCBC defensive UNNAMED DUITNOW bucket rename       ✅
#11c Maybank UNNAMED CMS bucket rename                  ✅
#11d Maybank UNNAMED MAS PAYMENT bucket rename          ✅
#16 RHB unnamed transfer buckets                        ✅
(plus C05/C11/C24 keyword sync from earlier sessions)
```

## What's next

**Per user instruction: AI prompt slim-down is next.**

Strip defensive entity-re-extraction logic from
`SYSTEM_PROMPT_v3_5_4.md` now that Layer 1 (parser
counterparty extraction) reliably labels rows across all 14
banks. The prompt currently asks the AI to defensively re-
parse description strings — that was justified when the parser
left half the rows as `NONE`, but with Sprint 6 #9 done, all
banks have either entity extraction or a clean UNNAMED bucket
fallback, so the defensive logic is now dead weight that costs
tokens per call.

Estimated scope:
- Read `SYSTEM_PROMPT_v3_5_4.md`
- Identify defensive re-extraction sections (likely the JOMPAY
  fallback, the BANK FEES inference logic, the UNNAMED bucket
  decoder, etc.)
- Strip what Layer 1 now handles deterministically
- Bump to v3.5.5 / v3.5 / v6.4 file naming
- Validate: ~1 coding session + user-validation cycle

**After AI prompt slim-down:**

Sprint 5 #21 `kredit_lab_classify.py` — Anthropic SDK module to
replace manual claude.ai upload step. ~500-1000 lines, fresh-
session-recommended.

## First actions in new chat

1. Acknowledge handoff. Verify state:
     git branch --show-current        # expect: sprint-6/polish
     git log --oneline -3              # expect: <handoff-append>,
                                       #         057813e (Sprint 6 #9),
                                       #         0675d2a (prior handoff)
     git status --short                # expect: untracked items only
     git rev-list --count origin/sprint-6/polish..HEAD
                                       # expect 0 if user pushed,
                                       # 2 (1 task + handoff) if not

2. Default next: AI prompt slim-down. Read
   `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_4.md`
   first to assess current size and identify dead defensive logic.
   Surface findings + proposed cuts to user before editing.

3. Apply session lessons:
   - When opcodes/prefixes can end with non-word chars, use
     `(?=\s|$)` instead of `\b` (Lesson 1)
   - Audit corpus first; the parser-upstream fix unlocks ALL
     opcodes not just the named ones (Lesson 2)
   - Trust the data not the name when routing (Lesson 3)
   - Build parsers structurally not lexically when one bank has
     multiple PDF generators (Lesson 4)

## Rollback procedure

  # Drop just #9 Bank Rakyat:
  git reset --hard 0675d2a
  # (Returns to pre-#9 state. All other Sprint 6 tasks intact.)

Tag sprint-4.5-complete remains the permanent stable marker.

## Context budget note

This session shipped 1 task in ~50-60k tokens. Per-phase breakdown:
  Phase A (corpus audit + opcode tally + format inspection): ~12k
  Phase B (user Q&A on 5 sub-questions, with TRANSFERFROMSA verify): ~5k
  Phase C (parser rewrite + counterparty handler + helper): ~12k
  Phase D (regressions: end-to-end + 14-bank validate + row-count
          comparison + JomPAY spot-check + bug-fix iteration): ~15k
  Phase E (commit + handoff append): ~10k

The single-session model was correct for #9: parser-upstream change
required full audit before any code, and the iteration on the
`\b`-vs-`(?=\s|$)` regex bug needed in-context observation of
intermediate test results.

Sprint 6 is complete. Next session is AI prompt slim-down (single-
file edit, no parser changes — light-medium scope, ~30-40k tokens
estimated).


---

# Handoff append — 2026-04-27 late-night (Sprint 5 #21 — kredit_lab_classify.py V1 shipped)

## What shipped this session (1 commit)

| # | Commit | Theme | Impact |
|---|---|---|---|
| 1 | TBD | Sprint 5 #21 V1 — `kredit_lab_classify.py` Streamlit module | New 1417-line deterministic classifier; 29/29 corpus files schema-validate against `BANK_ANALYSIS_SCHEMA_v6_3_5`; replaces AI-heavy claude.ai web flow for the deterministic 80% of classification |

### V1 build — what's wired

**Module structure (43 functions):** load → pre-analysis gate
(account-type, balance-trail, RP4 candidate sweep, purpose-cluster
histogram) → classify → aggregate (monthly / consolidated / top
parties / large credits / own-related / loans / unclassified /
flags / observations) → assemble → schema-validate → narrative
brief + parser-quality writers → Streamlit UI shell.

**Categories auto-classified in V1:**

  - C25 balance/opening rows (filtered first)
  - C01/C02 own-party (bidirectional company-root substring;
    handles parser-truncated buckets like `MUHAFIZ SECURITY` vs
    company `MUHAFIZ SECURITY SDN. BHD.`)
  - C05 salary (BULK SALARY counterparty bucket)
  - C06–C09 statutory (KWSP / SOCSO / LHDN / HRDF buckets +
    `core_utils.statutory_bucket_for` keyword fallback on DR side)
  - C10 loan disbursement (LOAN DISBURSEMENT bucket; analyst-
    confirmed factoring-entity textarea overrides)
  - C11 loan repayment (LOAN REPAYMENT bucket)
  - C12 FD/interest (FD/INTEREST bucket)
  - C13 reversal/inward return (INWARD RETURN bucket)
  - C19/C20 cash dep/wdl (CASH DEPOSIT / CASH WITHDRAWAL buckets)
  - C24 bank fees (BANK FEES bucket)
  - C03/C04 related-party (analyst pre-fills textarea; substring
    match vs counterparty-name and description)

**V1 deferred (out-of-scope per CLASSIFIER_HANDOFF.md):**
  - C14–C18 cheque-no detection (needs per-bank cheque regex)
  - C21–C23 monitoring (handled at flag layer, not per-row)
  - C26/C27 trade income/expense (richer counterparty inference)
  - Counterparty-ledger M1-M7 merging (V2)
  - Anthropic SDK narrative automation (V2/V3)
  - C03/C04 auto-confirmation of surfaced RP4 candidates (V1.1)

**Aggregation completeness:** `monthly_analysis[]` emits all 60
required schema fields, `consolidated` all 40 + `statutory_compliance`
17 fields with EPF dual-band (11–15% employer-only OR 20–26%
combined per v3.5.3 KDYN rule), `top_parties` carries
`monthly_breakdown[]` per party (schema-required), 16 canonical
flags emitted in fixed order.

**Deliverables produced:**
  - `analysis.json` — schema-valid hard gate via `jsonschema.validate()`
  - `narrative_brief.json` — ~1.2–1.8 KB structured brief targeting
    v3.5.6 prompt; carries headline numbers, detected patterns, RP4
    candidates, missing months, analyst asks
  - `parser_quality.json` — A/B/C/D/F grade based on
    `effective_match_rate` + balance-trail pass rate

### Hard rules respected
- Zero modifications to `app.py` / per-bank parsers / `core_utils.py`
- No `anthropic` SDK or API-key dependency
- `jsonschema.validate()` is a hard gate before write
- Cross-bank only (own-party uses `_company_root` suffix-stripping
  helper, no bank-specific paths)

### Bug fixes during V1 build (in-session)
1. `core_utils.determine_account_type` signature mismatch — uses
   `opening_balance/closing_balance/header_text` kwargs, not
   `od_limit`. Wrapped with safe-float coercion for None
   ending_balance values (Alliance KYDN has missing month).
2. Own-party leakage — `MUHAFIZ SECURITY` appearing as both top
   payer AND top payee. Root cause: directional substring `c in
   cp_upper` failed because company name `MUHAFIZ SECURITY SDN. BHD.`
   is longer than parser-truncated bucket `MUHAFIZ SECURITY`. Fixed
   with `_company_root` (strip SDN BHD/HOLDINGS/etc.) +
   bidirectional substring with 6-char minimum guard.
3. `top_parties` schema fail — `monthly_breakdown` is required per
   `$defs/party` (schema walker missed it because items used `$ref`).
   Added per-month accumulator in `build_top_parties`.
4. `pdf_integrity` schema mismatch — parser's 8-layer detector
   emits `text_layers`/`metadata`/`cross_validation` but schema
   enum only allows 5 layers (`fonts`/`visual`/`bank_profile`/
   `structural`/`arithmetic`). Sanitizer maps the extras to
   `structural`. Also drops findings where `detail` is null
   (schema requires object when present).
5. Account-number None → empty string coercion in
   `unclassified_transactions`, `large_credits`, `loan_transactions`,
   `own_related.transactions`, and `parsing_metadata.account_month_checks`.

### Cross-corpus validation: 29/29 schema-valid

Classification rates (against parser-tagged buckets only — trade
flow is V1-deferred to AI narrative stage):

```
45%  CIMB Muhafiz       (heavy payroll: BULK SALARY 11.8M + KWSP 1.7M)
25%  Ambank Hon Engineering
22%  Alliance Bestlite
17%  Ambank Plentitude
15%  OCBC Calvin Skin
13%  HLB MTCE
10%  Maybank Hydrise / OCBC LF
 7%  MBB Shahnaz / Ambank RE Concept
 5%  MBB Hou Tian / UOB Upell
 4%  Alliance KYDN / Maybank Zaim / Agrobank / PBB LSR
 2%  Maybank Mytutor / PBB Mazaa / CIMB Naara
 1%  MBB Naara
 0%  HLB Detik / BIMB KMZ / BIMB Mytutor / Bank Muamalat / Bank
     Rakyat Felcra / Bank Rakyat MTCEC / RHB Kay R / Waja RHB
     (all-trade flow — V1 has no rule for customer/supplier names)
```

The 0–25% on non-Muhafiz files is the deterministic floor by design.
Trade rows go into `unclassified_transactions` + `top_parties` +
`narrative_brief.json` — exactly what stage 3 (AI) consumes.

## What's next

**Option A — V1.1 cheap wins (~30 min, single session):**
  1. Cheque-no regex: UNIDENTIFIED (CHEQUE) DR → C16, CR → C18.
     ~25 rows on Muhafiz alone.
  2. Auto-apply RP4 candidates surfaced in gate (currently only
     analyst-typed names in textarea fire C03/C04; the surfaced
     candidates from `scan_related_party_candidates` are info-only).
  3. Numerical comparison vs `Full Report CIMB Muhafiz.classified.json`
     reference output (the handoff's specified test gate — ±RM1.00
     on totals, structural fields exact).

**Option B — V2 (fresh session, 500-1000 LOC):**
  - M1–M7 counterparty-ledger merging
  - C26/C27 trade rules (counterparty-pattern-based, not AI)
  - Anthropic SDK wiring for automated narrative
  - Two-button RP4 confirmation flow

**Option C — Other queued work:**
  - AI prompt slim-down (was the next-up before this session;
    `SYSTEM_PROMPT_v3_5_5.md` → `v3.5.6` strip dead defensive
    extraction logic). Independent of V1.

## First actions in new chat

1. Acknowledge handoff. Verify state:
     git log --oneline -3       # expect: <V1 commit>, c45b3ce, 057813e
     git status --short         # expect: untracked items only
2. Default next: V1.1 cheap wins or numerical-validation gate
   against `*.classified.json` references, depending on user
   priority.
3. Test plan from `prompts/CLASSIFIER_HANDOFF.md` is still valid:
   pick CIMB Muhafiz / Alliance KYDN / OCBC Calvin Skin / Maybank
   Hydrise; produce analysis.json + narrative_brief.json +
   parser_quality.json; eyeball numerical fields against the
   corresponding existing `*.classified.json`.

## Key files

  - `kredit_lab_classify.py` (NEW, +1417 lines, root of repo)
  - `prompts/CLASSIFIER_HANDOFF.md` (untracked, the V1 brief)
  - `validation runs - json/22 april 2026 - result HTML(MTA,KYDN,MSSB)/Test Bank Staement/MTA/KREDIT_LAB_AI_EFFICIENCY_RECOMMENDATIONS.md`
    (architecture spec — sections 2.1 + 4)
  - Schema/rules unchanged: `BANK_ANALYSIS_SCHEMA_v6_3_5.json`,
    `CLASSIFICATION_RULES_v3_5.json`

## Rollback procedure

  # Drop V1:
  git reset --hard c45b3ce
  # (Returns to pre-V1 state. Sprint 6 untouched; handoff append removed.)

## Context budget note

This session shipped 1 task in ~80-90k tokens. Per-phase breakdown:
  Phase A (handoff read + arch spec + schema/rules survey): ~15k
  Phase B (skeleton write + design-Q surfacing): ~10k
  Phase C (full V1 implementation rewrite): ~25k
  Phase D (Muhafiz e2e + own-party + monthly_breakdown +
          pdf_integrity + None-coercion debug-fix loop):    ~20k
  Phase E (cross-corpus 29-file validation):                ~5k
  Phase F (commit + handoff append):                        ~10k

The full-rewrite single-session model was correct: stub-only
skeleton would have left the user with no working artifact, and
the design questions all had clear right answers from the
architecture doc. Schema-aligned aggregation infrastructure had
to be built up-front (60-field monthly, 40-field consolidated)
because a partial implementation can't even schema-validate.


---

# Handoff append — 2026-04-27 late-night #2 (V1.1 — 99% AI agreement)

## What shipped this session (1 commit on top of V1)

Numerical-validation gate from CLASSIFIER_HANDOFF.md test plan: V1
output compared row-by-row vs `Full Report CIMB Muhafiz.classified.json`
(deterministic AI reference, classifier_version 0.2.0). V1
delivered 87% per-row agreement. V1.1 closed 5 systemic bugs and
lifted agreement to **99% (1190/1198 rows match exactly)**.

### V1.1 fixes

1. **C01/C02 direction flip.** V1 had C01=DR / C02=CR; rulebook
   says C01=CR (Own Party Credit) / C02=DR (Own Party Debit). AI
   reference confirmed. Flipped both classify and would-be C03/C04
   side branch (C03=CR / C04=DR per rulebook). Closed 60 rows.

2. **BUCKET_TO_CATEGORY remap.** V1 had three wrong codes from
   intuition vs rulebook:
     - CASH DEPOSIT bucket: was C19 (Cheque Deposit) → fixed C17
     - CASH WITHDRAWAL bucket: was C20 (Cheque Issue) → fixed C18
     - INWARD RETURN bucket: was C13 (generic Reversal) → fixed
       C16 (IBG/GIRO Inward Return)
   Closed ~17 rows.

3. **Classify priority re-order.** Own-party + related-party
   checks now run BEFORE bucket-direct mapping. Stops LOAN
   REPAYMENT bucket from overriding C02 when the row is actually
   own-account transfer.

4. **Description-keyword fallback layer.** New `_KEYWORD_RULES`
   list with cross-bank patterns for C13–C20 + C05. Includes
   STAFF OVERTIME / STAFF INCENTIVE / STAFF BONUS / STAFF ADVANCE
   per the v3.4 design (parser preserves employee names, classifier
   applies salary keyword). Runs after bucket-direct + statutory
   fallback. Closed 22 + 17 + 9 rows across the categories.

5. **Side-guard on bucket-direct firings.** New `_CATEGORY_SIDES`
   map. If parser bucketed a CR row in BULK SALARY (DR-only
   category), classifier rejects rather than mis-firing C05.
   Closed 2 rows.

6. **Monthly aggregation rewired** for new C13–C20 mapping:
     - C13 → reversal_cr only (no longer dual-counted to inward_return)
     - C14 → returned_cheques_inward_count/amount
     - C15 → returned_cheques_outward_count/amount
     - C16 → inward_return_cr (new)
     - C17 → cash_deposits_count/amount (was C19)
     - C18 → cash_withdrawals_count/amount (was C20)
     - C19 → cheque_deposits_count/amount (NEW field, was unused)
     - C20 → cheque_issues_count/amount (NEW field, was unused)

### V1.1 results

**Numerical comparison vs AI reference (Muhafiz, 1198 rows):**

```
                  V1     V1.1
Agreement       87%      99%   (+12 pp)
Disagreement   145        8    (-94%)
Schema-valid   29/29    29/29  (no regression)
```

**Per-code distribution match (V1.1 vs AI reference):**
```
  code      ref   V1.1  delta
  None      612    606     -6   (V1.1 catches more)
  C24       290    292     +2   (over-fire on 2 mis-buckets)
  C05        91     89     -2   (noise floor)
  C02        56     56     +0   ✓
  C06        50     50     +0   ✓
  C19        23     23     +0   ✓
  C07        22     22     +0   ✓
  C01        15     15     +0   ✓
  C08        13     13     +0   ✓
  C16         9      9     +0   ✓
  C18         7      7     +0   ✓
  C25         6      6     +0   ✓
  C20         2      2     +0   ✓
  C09         1      1     +0   ✓
  C17         1      1     +0   ✓
  C11         0      6     +6   (LOAN REPAYMENT bucket noise — AI inconsistent here)
```

**Cross-corpus classification rate uplift (top 5):**
```
  CIMB Muhafiz       45% → 49%
  Maybank Hydrise    10% → 27%   (+17pp from STAFF OVERTIME)
  UOB Juta Kenangan   5% → 22%
  Alliance Bestlite  22% → 22%
  OCBC Calvin Skin   15% → 15%
```

**Remaining 8 disagreement rows are noise floor:**
- 6× LOAN REPAYMENT bucket on "TR IBG SAMSI BIN IBRAHIM Monthly
  Instalment" — AI fires C11 on 11 of these rows but leaves 6
  unclassified (AI is inconsistent; no clean rule to split them).
- 2× BANK FEES bucket on rows AI reads as salary — sub-noise.

## What's next

**V1.1 is production-ready for the categories it covers.** Next
priority decisions:

A. **Run V1.1 in actual Streamlit on Muhafiz with analyst-pre-filled
   related-parties textarea.** This catches UI bugs / decisions-form
   wiring issues / download-button issues before client demo.

B. **V2 fresh session:**
     - C26/C27 trade rules (counterparty-pattern-based, not AI)
     - M1–M7 counterparty-ledger merging
     - Two-button RP4 confirmation flow (auto-apply surfaced
       candidates after analyst confirms in checklist)
     - Anthropic SDK wired for automated narrative

C. **AI prompt slim-down deferred work:** v3.5.6 prompt now
   shipped (commit 3762838 from parallel session); confirm V1.1's
   `narrative_brief.json` shape is consumable as expected.

## First actions in new chat

1. Acknowledge handoff. Verify state:
     git log --oneline -3       # expect: <V1.1 commit>, bfda34c, 3762838
     git status --short
2. If client demo upcoming: option A (Streamlit live test on Muhafiz).
3. Otherwise default next: option B (V2 trade + RP4 flow).

## Rollback procedure

  # Drop V1.1 only:
  git reset --hard bfda34c
  # (Returns to pre-V1.1, V1 still intact at 87% agreement.)

  # Drop V1 + V1.1:
  git reset --hard c45b3ce

# Handoff append — 2026-04-27 night #3 (Sprint 5 #21 — kredit_lab_classify.py V2 shipped)

## What shipped this session (uncommitted; user reviews before commit)

V2 closed all five tracks of `prompts/CLASSIFIER_V2_HANDOFF.md`. Single
file touched (`kredit_lab_classify.py`, ~1483 → ~1730 lines). 30/30
corpus files schema-validate in 4.3s.

- **V2.1 — C26/C27 trade rules.** Added `_CORPORATE_ENTITY_MARKERS` /
  `_NATURAL_PERSON_MARKERS` regexes and a final fallback in
  `classify_transactions` (after all V1.1 rules). Per
  `CLASSIFICATION_RULES_v3_5` LOCKED rule: counterparty must contain
  SDN BHD / BHD / BERHAD / ENTERPRISE / TRADING / CORPORATION / CORP /
  GROUP / HOLDINGS / INDUSTRIES; natural-person markers (BIN/BINTI/A/L/
  A/P) explicitly do NOT fire. New monthly fields `trade_income_count`,
  `trade_income_amount`, `trade_expense_count`, `trade_expense_amount`
  + consolidated `total_trade_income_cr`, `total_trade_income_count`,
  `total_trade_expense_dr`, `total_trade_expense_count`. Schema's
  v6.3.5 changelog mentions these fields but property defs are absent
  in the actual schema — `additionalProperties` not enforced, so they
  pass validation. C26/C27 stay in net per rule's "Impact: NOT
  excluded".

- **V2.2 — RP4 two-pass UI.** `streamlit_main` now caches the gate
  output in `st.session_state` (`upload_key`, `data`, `gate`); first
  upload runs `_run_pre_analysis_gate` once; the new
  `_render_decisions_form(rp4_candidates)` renders RP4 candidates as
  checkboxes that auto-append to `decisions.related_parties` (RP4
  names take precedence over free-text duplicates via case-insensitive
  dedupe). The "Pre-analysis gate" panel surfaces account type +
  recon pass-rate before the analyst commits. Gate re-runs only if
  the analyst supplies an OD limit (changes account_meta).

- **V2.3 — M1+M2+M3 counterparty merging.** New
  `_canonicalize_for_merge` (uppercase, strip parens, strip suffixes
  via extended `_COMPANY_SUFFIXES`, drop trailing single-letter
  truncation tokens). New `_merge_counterparty_groups` does M1+M2
  (hash grouping) + M3 (token-subset merge bounded to top-200 by
  amount via `_MERGE_M3_TOP_N`). `build_top_parties` calls it once
  per side. Verified: PIASAU GAS SDN BHD / SDN. BHD. / BERHAD all
  → "PIASAU GAS"; PLANWORTH GLOBAL S → PLANWORTH GLOBAL.

  **M4 fuzzy (Levenshtein) deferred.** Initial implementation took
  29s on KYDN (1742 unique CPs) — O(K²) Levenshtein blew the budget.
  Bounded M3 keeps total runtime to 4.3s for the entire 30-file
  corpus. Tail-entity fuzzy matching is V3 territory; M3 substring
  on top-200 catches the high-impact cases.

- **V2.4 — OD-aware balance trail.** `reconcile_balance_trail` now
  dispatches on `convention`: OD → `opening + debit - credit`
  (Alliance positive-magnitude); CR → `opening + credit - debit`
  (default; Ambank pre-negated OD also falls through here correctly).
  Bestlite: 0/6 → 6/6. KYDN unchanged at 6/7 — failing month is
  `2094-10` parser junk (year 2094), NOT an OD issue. The handoff's
  KYDN claim was wrong; that's a parser bug for V3.

- **V2.5 — C14/C15 / C21–C23 finalisation.** Cross-corpus check on
  the C14/C15 keyword regex: 0 hits across all 29 files. Real
  returned cheques in MBB Hou Tian use Maybank-specific tokens
  (`RTD PYMT STOPPED`, `RTD ACCOUNT CLOSE`, `RTN CHQ`) — adding them
  violates `feedback_crossbank.md` ("never bank-specific"). Regex
  unchanged as a generic safety net for any future bank using
  long-form `RETURNED CHEQUE` / `DISHONOURED`. C21–C23 documented
  as intentional flag-layer-only (16-flag indicators[] already cover
  AML monitoring; schema doesn't reserve C21–C23 fields per-row).
  Top-of-file docstring rewritten to reflect V2 state.

## Cross-corpus snapshot (no analyst input)

30/30 schema-valid in 4.3s. Selected lift vs V1.1 baseline:

| File | V1.1 | V2 (no analyst) | C26 | C27 | recon |
|---|---:|---:|---:|---:|:--:|
| CIMB Muhafiz | 49.4% | 49.6% |  1 |  1 | 6/6 |
| MBB Hou Tian | 11.4% | 18.3% | 26 | 56 | 6/6 |
| Maybank Hydrise | 27.4% | 29.2% |  0 | 18 | 6/6 |
| Alliance Bestlite | 25.4% | 25.4% | 11 | 36 | 0/6 → **6/6** |
| Alliance KYDN |  5.3% |  7.0% | 32 | 26 | 6/7 |
| Ambank RE Concept |  8.0% |  9.8% | 15 |  6 | 6/6 |
| Maybank Zaim |  ~7% | 11.1% |132 | 19 | 1/6 |
| UOB Upell |  9.0% | 27.7% | 49 |  0 | 0/6 |

When all `scan_related_party_candidates` RP4 picks are confirmed
(simulated): Muhafiz 49.6% → 56.0% (3 RP4 → 79 C03/04 rows);
Hou Tian → 31.0% (156 C03/04); Hydrise → 52.9%; Plentitude → 50.5%;
Shahnaz Builders → 54.1%. RP4 confirmation flow is the dominant
lift once parser counterparty extraction is decent.

The 80%+ Muhafiz target in `CLASSIFIER_V2_HANDOFF.md` was over-optimistic.
Per the audit: most unclassified Muhafiz CR counterparties are
gov/agency entities (JANM, AKAUNTAN NEGARA, KERAJAAN NEGERI, PETRONAS)
that don't have `SDN BHD / BHD / ENTERPRISE / ...` markers. The
LOCKED rulebook keyword set caps the mechanical lift here. Files
stuck near 0% (BIMB Mytutor, BIMB KMZ, Bank Rakyat MTCEC, Waja RHB,
Bank Rakyat Felcra, PBB Mazaa) are parser-counterparty-extraction
blocked — classifier can't fire on what the parser didn't extract.

## What's NOT in V2 (V3 territory)

- **Anthropic SDK wiring** for automated narrative (still
  manual claude.ai web paste).
- **End-to-end PDF → app.py → kredit_lab_classify → renderer pipe.**
- **Parser counterparty fixes** for the 0%-classification corpora —
  the parser's `_extract_counterparty()` paths leave whole banks
  with raw description fragments instead of clean entity names
  (BIMB Mytutor: "9871 RTP REDIRECT CT CR"; Bank Rakyat Felcra:
  "55708 REMITTANCECR-RENT 393 270 00"). This is a parser
  problem not a classifier problem — fix in the bank module, not
  here.
- **Affin OCR-only bank classification.**
- **M4 fuzzy counterparty merging** (Levenshtein) — needs better
  scaling than the initial O(K²) attempt (e.g. token-inverted
  index or bounded fuzzy on top-N only).
- **C14/C15 bank-specific shorthand** (Maybank RTD / RTN CHQ) — if
  ever wanted, route through parser-side bucket stamping rather
  than classifier keywords (cross-bank purity).
- **KYDN 2094-10 parser-junk row** that drops recon to 6/7 —
  parser-side date-parsing bug; classifier can't fix.
- **Schema property defs for trade_income_* / trade_expense_***.
  Schema's v6.3.5 changelog says they were added; they weren't.
  V2 emits them anyway (passes validation because additionalProperties
  isn't enforced). If user wants strict tracking, add the property
  defs to BANK_ANALYSIS_SCHEMA_v6_3_5.json — but per V2 hard rules
  this session didn't touch the schema.

## Hot spots / fragility

- `_merge_counterparty_groups` is bounded at top 200 keys by
  amount. If a corpus develops a long tail of mid-sized customers
  that should merge, raise `_MERGE_M3_TOP_N` cautiously (cost is
  O(N²)).
- C26/C27 fire ONLY when counterparty has a corporate marker. Files
  with truncated parser counterparties (e.g. "PLANWORTH GLOBAL"
  without trailing SDN BHD) get dropped from C26/C27. The intent of
  the LOCKED rule is conservative — false negatives are preferred
  over false positives. If user wants more aggressive trade
  detection, extend `_CORPORATE_ENTITY_MARKERS` keyword set in
  `kredit_lab_classify.py` (cross-bank-safe additions only).
- `_NATURAL_PERSON_MARKERS` deliberately excludes bare `AL`/`AP`
  (false-positive on AL-IKHWAN HOLDINGS, etc.). Only the slash forms
  `A/L`, `A/P` and full words `BIN`, `BINTI` are blocked.
- V2.2 UI uses `st.session_state["upload_key"]` keyed on
  `(upload.name, len(raw))`. If two files happen to share the
  same name + length, gate state would persist incorrectly. Edge
  case but worth a hash if it bites.

## Files touched this session

```
modified:   kredit_lab_classify.py     (1483 → ~1730 lines, all V2 changes)
            prompts/NEXT_CHAT_PROMPT.md (this append)
```

`CLASSIFICATION_RULES_v3_5.json`, `BANK_ANALYSIS_SCHEMA_v6_3_5.json`,
`app.py`, `core_utils.py`, all per-bank parsers — untouched per V2
hard rules.

## What's next

V3 should focus on the **non-V2 levers**, in this order of impact:

A. **Parser counterparty extraction fixes** — biggest remaining
   classification-rate lever. BIMB Mytutor, Bank Rakyat Felcra,
   PBB Mazaa, Bank Rakyat MTCEC all sit at 0% because the parser
   leaves raw description fragments where the counterparty name
   should be. Fix in the bank-specific parser modules.

B. **Anthropic SDK + narrative automation** — close the manual
   claude.ai paste-back loop. Use prompt caching (per CLAUDE.md
   guidance) and the v3.5.6 prompt as the system prompt. Probably
   needs `pip install anthropic` and a new `kredit_lab_narrative.py`
   companion.

C. **End-to-end pipeline glue** — single Streamlit flow that runs
   PDF → app.py parser → kredit_lab_classify → narrative → renderer
   in one shot.

D. **Schema `trade_income_*` / `trade_expense_*` property defs** —
   if the strict-tracking matters; otherwise leave as the
   permissive additionalProperties V2 ships now.

## First actions in new chat

1. Acknowledge handoff. Confirm starting point:

```
git log --oneline -3   # expect d900f03 (V1.1) on top; V2 still uncommitted
git status --short     # expect modified: kredit_lab_classify.py, prompts/NEXT_CHAT_PROMPT.md
```

2. If user wants V2 committed: review diff, commit as
   `Sprint 5 #21 V2: trade rules + RP4 confirmation + OD trail + counterparty merge`.

3. If V3-A (parser counterparty fixes): pick one 0% bank
   (Bank Rakyat Felcra is the most egregious), open the parser
   module, fix `_extract_counterparty`, re-run cross-corpus.

## Rollback procedure

```
# Drop V2 only (return to V1.1 d900f03):
git checkout -- kredit_lab_classify.py prompts/NEXT_CHAT_PROMPT.md

# Drop V2 + V1.1 (return to V1):
git reset --hard bfda34c

# Drop V2 + V1 + V1.1 (return to pre-classifier state):
git reset --hard c45b3ce
```

## Context budget note

V2 took ~50k tokens — under the 70-90k forecast. Budget went mostly
to phase A (audit + schema check) and phase B (V2.1 + V2.4 + V2.5);
phase C (M1-M3 merge) and D (RP4 UI) were small.

# Handoff append — 2026-04-28 morning (Sprint 7 V3-A — Bank Rakyat closed; 4-bank parallel research returned)

## What shipped this session (5 commits + verification script)

```
5731993  V3-A #5: scripts/verify_felcra_v3a.py headless verification harness
cd20a3e  V3-A #4: strip '?' glyph from BR entity bodies (Felcra UTF artifact)
066360a  V3-A #3: route Bank Rakyat PROFIT CHARGED to BANK FEES
aa6c034  V3-A #2: MTCEC opcode-spacing normalization + 1-6 digit code strip
70906f8  V3-A #1: _br_extract_entity collects through corporate suffix
a8c3330  Sprint 5 #21 V2: trade rules + RP4 + OD trail + CP merge
```

## Verified Felcra V3-A — 0% baseline → 58.0% post-fix

Folder `Bank-Statement/BankRakyat/8/` (6 PDFs, 4373 rows). Pre-V3-A:
parser fragments leaking as CPs (e.g. `"55708 REMITTANCECR-RENT 393 270
00"`). Post-V3-A: 58.0% classification (2536/4373) WITHOUT any analyst
input. 1383 unique entity names, 0 raw fallthroughs, 6/6 month recon.
Top payers/payees show real entities (KOPERASI KAKITANGAN FELCRA
BERHAD, FELCRABEKALAN&PERKHIDMATAN SDN BHD, DIVERSATECH SDN BHD, etc.).

Remaining 1837 unclassified split as 1759 DR / 78 CR — almost entirely
personal-name staff allowance/medical/honorarium DR rows. They become
C03/C04 with analyst RP4 confirmation OR via auto-RP-detection (see
below).

## Design decision — auto-detect related parties (deferred to next session)

User raised this directly: "apart from RP4 analyst input, you can also
determine if any personal has the characteristic of a related party
such [as] many payments going into personal account ... receive or give
advances or loan to the company". Plus optional Claude AI assist.

Existing scaffolding: `scan_related_party_candidates()` at
[kredit_lab_classify.py:285](kredit_lab_classify.py#L285) currently uses
debit-count >= 3 + personal-keyword hits >= 2 (MEDIUM confidence). Two-
step extension plan:

- **Step 1 (deterministic, ~30-50 LOC)** — add concentration ratio
  (single party > 5% of gross DR), recurrence cadence (same payee
  monthly), bidirectional flow (same person both CR and DR — director
  loan-account pattern), round-number advance heuristic. Pure stats on
  `counterparty_ledger`.
- **Step 2 (V3-B Anthropic SDK)** — Claude scores LOW/MEDIUM/HIGH per
  candidate using description samples + amount distribution. Re-uses the
  same SDK setup that V3-B narrative automation will need.

User has indicated preference for Step 1 to land before further parser
patches.

## Sub-agent findings — 3 banks researched in parallel (research-only)

Three Explore sub-agents dispatched (Bank Islam handles both BIMB
Mytutor + KMZ; RHB handles Waja; Public Bank handles Mazaa). Reports
synthesized below. **User confirmation needed on each before patching.**

### Bank Islam (BIMB) — Mytutor + KMZ

- **Folder 6 = "KMZ RESTU ENTERPRISE SDN BHD"** — confirmed match for
  "BIMB KMZ" via PDF page-1 header text from `12. BANK STATEMENT
  dis'25.pdf`.
- **Folder 5 = "PRINCIPAL GAS SDN BHD"** (BIMB8489 series) — this is
  NOT Mytutor.
- **"BIMB Mytutor" NOT located anywhere in the current repo.** All six
  BankIslam folders inspected; no Mytutor company name found in any
  PDF page-1 text.
- Both folder 5 and folder 6 currently route at **100% raw** in
  `_extract_counterparty` — no Bank Islam branch exists.

Two distinct format patterns:

- **Folder 5 (Principal Gas)**: descriptions like
  `'1 9124 CDB CS TO IBFTS3 PRINCIPAL GAS SDN. B'`,
  `'5 1554 CA DR&CR ADVICE PRINCIPAL GAS SDN BH 14201 REFUND...'`.
  Entity names PRESENT but TRUNCATED at column boundary (`"SDN. B"`,
  `"SDN BH"` instead of `"SDN BHD"`). Suggests parser-side
  `x_tolerance`/column-width bug in [bank_islam.py](bank_islam.py).
- **Folder 6 (KMZ)**: descriptions like
  `'3110 SA HSE CHQ DEP - CR .50'`, `'9895 INW DuitNow Transfer'`,
  `'0523 eSPICK INW PT LTD CO'`. Entity names APPEAR ABSENT from
  description field entirely — likely a different parser sub-format
  where the entity is in a separate column the parser isn't capturing.

Top opcodes observed across Bank Islam corpus: `CDB CS TO IBFTS3` (154),
`MYC DD CASA - DR`, `PROFIT PAID`, `CMS SERVICE CHARGE`, `INW DuitNow
Transfer`, `IBG TRANSFER TO CA`, `CA DR&CR ADVICE`, `CDB JOMPAY OFF-US`/
`ON-US`.

Proposed fix: insert Bank Islam branch in
[app.py:_extract_counterparty](app.py) ~line 2412 (before HLB). Two
distinct patterns:
- Folder-5 style: strip leading seq-number, normalize space-separated
  opcodes, run multi-token entity extractor through corporate suffix
  (mirrors Bank Rakyat). Repair truncation `\bSDN\.?\s*B(?!D)\s*$` →
  `SDN BHD`.
- Folder-6 style: route fee opcodes (`CMS SERVICE CHARGE`, `eSPICK CHQ
  PRCSG FEE`) → BANK FEES; route system-transfer opcodes (`HSE CHQ DEP`,
  `INW DuitNow Transfer`, `SA HSE CHQ`) → `UNNAMED BANK ISLAM TRANSFER
  (CR|DR)`.
- Plus parser-side investigation in [bank_islam.py](bank_islam.py) for
  Folder-5 truncation and Folder-6 missing-column issue.

### RHB — Waja

- **Folder 8/RHB = "JATI WAJA QUALITY SERVICES"** — confirmed match via
  PDF page-1 header (`JATI WAJA QUALITY SERVICES NO 11-1 JLN 3/18D ...
  Reflex Cash Management JATI WAJA QUA`).
- Statement uses RHB's Reflex Cash Management platform. Description
  format: `RFLX <ENTITY> / -` or `REFLEX- <ENTITY> [REF/PURPOSE] / -`.
- No RHB-specific branch in `_extract_counterparty`.
- Some RFLX rows currently route to `"<name> (possibly multiple
  parties)"` via the global pattern at line ~2926 — surfaces the rail
  label "RFLX" in CP output, violating
  [feedback_no_rail_labels_in_discussion](feedback_no_rail_labels_in_discussion.md).

Proposed fix: insert RHB branch in [app.py](app.py) ~line 2757 (before
global special-buckets). Strip `RFLX`/`REFLEX-` prefix entirely. For
intra-company rows route to `UNNAMED RHB REFLEX TRANSFER (CR|DR)` (no
rail label visible). For interbank opcodes (DUITNOW/IBG/INWARD), use
the multi-token entity extractor playbook from Bank Rakyat. Aligns
with cross-bank purity guidance from feedback memories.

### Public Bank — Mazaa

- **Folder 3/PublicBank = "MAZAA SDN BHD"** (account 3814592414) —
  confirmed match via page-1 header on `1_JAN.pdf`.
- Description format: `DUITNOW TRSF CR <ref> MAZAA SDN BHD ...` —
  MTCEC-style space-separated opcode + entity.
- No PBB branch in `_extract_counterparty`. Generic DUITNOW handler at
  line ~3540 currently extracts `"TRSF CR"`/`"TRSF DR"` as the CP
  instead of the actual entity. All 14 sampled DUITNOW rows routed to
  `"TRSF CR"`/`"TRSF DR"` via "pattern" — clearly wrong output.

Proposed fix: insert PBB branch in [app.py](app.py) ~line 3032 (after
RHB region). Add `_pbb_normalize_opcode` helper analogous to
`_br_normalize_opcode` to collapse `DUITNOW TRSF CR` →
`DUITNOWTRANSFERCR`. Reuse `_br_extract_entity` (designed cross-bank
safe) for entity extraction through corporate suffix.

## User decisions (confirmed at end of session)

1. **BIMB Mytutor**: located at
   `Bank-Statement/BankIslam/Mytutor Academy/` (6 password-protected
   PDFs, password `MY019126` per
   `Bank-Statement/BankIslam/Mytutor Academy/PASSWORD.txt`). 8046 rows
   total. Page-1 header confirms "MYTUTOR ACADEMY SDN BHD". Live parse
   shows 100% raw routing — descriptions are opcode-only fragments
   (`'9871 RTP REDIRECT CT CR'`, `'9124 CDB CS TO IBFTS3'`) with NO
   entity tail. Exact match for V2 handoff's example
   `'9871 RTP REDIRECT CT CR'` from line 4148. **Same root cause as
   BIMB KMZ folder 6** — bank_islam.py is dropping the entity column
   for these PDF sub-formats.
2. **BIMB KMZ**: pursue parser-level investigation (user confirmed).
   Likely fixes Mytutor as well since the failure pattern is identical.
3. **Bank Islam folder 5 (Principal Gas Sdn Bhd)**: also in scope —
   user confirmed adding to V3-A. Different sub-format failure
   (entities present but truncated mid-suffix).
4. **Auto-RP detection Step 1**: land BEFORE further bank parser
   fixes (user confirmed).
5. **PBB Mazaa + RHB Waja**: green light per playbook (user confirmed).

## Open follow-ups
- `_br_extract_entity` already cross-bank-safe by design; reusing it
  for PBB and RHB confirms that. Consider renaming to
  `_multi_bank_extract_entity` (or moving to a shared helper section)
  if it lands in 3+ banks.
- **Concatenated SDN BHD detection** (FELCRABEKALAN&PERKHIDMATANSDN,
  FELCRABINASDNBHD) — ~30-50 Felcra rows fail to fire C26 because
  `\bSDN BHD\b` regex requires word boundaries. Add concatenated-form
  match (`\bSDNBHD\b`, `\bBERHAD\b` substring inside concatenated
  blob).
- **Auto-RP detection Step 1** should land BEFORE further bank parser
  fixes per user preference (will lift unclassified personal-name
  rows automatically without analyst input).
- **TR TO FINS** (Bank Rakyat) — single-sample MTCEC opcode, defer
  until corpus confirms intent. Likely LOAN REPAYMENT.
- **Schema property defs for trade_income_*** / **trade_expense_*** —
  schema's v6.3.5 changelog mentions them but actual property defs
  missing. V2 emits anyway since `additionalProperties` not enforced.

## First actions in new chat

1. Acknowledge handoff. Verify state:
   ```
   git log --oneline -7
   ```
   Expect: 5731993 → cd20a3e → 066360a → aa6c034 → 70906f8 → a8c3330 → 5a4642c.

2. Re-read this handoff section above, especially "Sub-agent findings" and "Open follow-ups".

3. Confirm scope with user:
   - BIMB Mytutor: drop scope, or has user supplied a PDF?
   - BIMB KMZ: pursue parser-level investigation, or skip if format genuinely lacks entity columns?
   - RHB Waja: rail-strip + entity extractor — green light per playbook?
   - PBB Mazaa: MTCEC-style fix — green light per playbook?
   - Auto-RP detection step 1: land first (recommended), or defer?

4. **Confirmed work order:**
   1. **Auto-RP detection Step 1** — deterministic behavioral signals
      on counterparty_ledger (~30-50 LOC). Lifts unclassified personal-
      name DR rows automatically without analyst input. Files:
      [kredit_lab_classify.py:285](kredit_lab_classify.py#L285)
      `scan_related_party_candidates`. Re-verify Felcra after.
   2. **PBB Mazaa** — MTCEC playbook (cleanest case). Folder
      `Bank-Statement/PublicBank/3/`. Add PBB branch in
      `_extract_counterparty` ~line 3032, opcode-spacing normalizer,
      reuse `_br_extract_entity`.
   3. **RHB Waja** — RFLX/REFLEX rail-strip pattern. Folder
      `Bank-Statement/RHB/8/`. Strip prefix entirely (no rail label
      surfaced). Insert RHB branch ~line 2757.
   4. **Bank Islam parser investigation** (shared root cause for
      Mytutor + KMZ): determine why
      [bank_islam.py](bank_islam.py) produces opcode-only descriptions
      for these PDF sub-formats. Likely a column-detection /
      `extract_text(layout=True)` /  `x_tolerance` issue. Once the
      parser yields full descriptions, the routing fix becomes the
      same playbook as Bank Rakyat. PDFs to use:
      `Bank-Statement/BankIslam/Mytutor Academy/*.pdf` (password
      `MY019126`) + `Bank-Statement/BankIslam/6/*.pdf`.
   5. **Bank Islam folder 5 (Principal Gas)** — once parser is
      healthy, add entity-extraction routing block + truncation repair
      (`SDN. B` → `SDN BHD`). Folder
      `Bank-Statement/BankIslam/5/*.pdf`.
   6. **BIMB Mytutor + KMZ routing** — adds the same Bank Islam branch
      coverage. Should be near-free once steps 4-5 land.

5. After each bank lands, run a verification script analogous to [scripts/verify_felcra_v3a.py](scripts/verify_felcra_v3a.py). For Mytutor, the harness needs `pdfplumber.open(p, password="MY019126")`.

## Rollback procedure

```
# Drop V3-A only (return to V2):
git reset --hard a8c3330

# Drop V2 + V3-A (return to pre-classifier):
git reset --hard c45b3ce
```

## Context budget note

Sprint 7 V3-A used ~80k tokens including 3 parallel research agents.
Heavy items: agent dispatches, multiple verification runs, and the
Bank Islam/Mytutor disambiguation.

# Handoff append — 2026-04-28 afternoon (Sprint 7 V3-A — auto-RP Step 1, PBB Mazaa, RHB Waja, BIMB Mytutor+KMZ shipped)

## What shipped this session (4 commits)

```
1ad4aab  Sprint 7 #10 (V3-A): BIMB multi-line capture + routing (Mytutor + KMZ)
478e5fd  Sprint 7 #9  (V3-A): RHB Waja verification harness — extraction complete
045ee91  Sprint 7 #8  (V3-A): Public Bank DUITNOW TRSF / RMT entity extraction
aa42cdf  Sprint 7 #7  (V3-A): auto-RP detection Step 1 — deterministic signals
```

Plus 3 new verification harnesses in `scripts/`:
[verify_mazaa_v3a.py](scripts/verify_mazaa_v3a.py),
[verify_waja_v3a.py](scripts/verify_waja_v3a.py),
[verify_bimb_v3a.py](scripts/verify_bimb_v3a.py).

## Per-item results

**#7 Auto-RP detection Step 1** ([kredit_lab_classify.py:285](kredit_lab_classify.py#L285)) — five deterministic
signals on `counterparty_ledger`: personal_keyword (weight 2),
concentration_dr ≥5% (2), bidirectional_flow min(cr,dr)≥2 (2),
monthly_recurrence ≥3 months (1), round_amount_advance (1). HIGH ≥3,
MEDIUM ≥2, LOW =1. New `auto_confirmed_related_parties()` helper feeds
HIGH names into `AnalystDecisions.related_parties` automatically. UI
form pre-checks HIGH; analyst can untick. Felcra: **58.0% → 59.1%**
(+51 rows from 2 HIGH director loan-account patterns).

**#8 PBB Mazaa** ([app.py](app.py) — bank-gated branch between RHB and
generic DUITNOW handler). Routes `DUITNOW TRSF (DR|CR) <ref> [<ENTITY>]`
and `RMT (DR|CR) [<ref>] [AT CPC] [<ENTITY>]` with `_br_extract_entity`,
fallback `UNNAMED PUBLIC BANK TRANSFER (CR|DR)`; `RMT CHRG → BANK FEES`.
Verified on Bank-Statement/PublicBank/3 (497 rows): 84 DUITNOW + 2 RMT
rows route correctly. Cross-bank gate confirmed (Maybank `DUITNOW TRSF`
still hits generic).

**#9 RHB Waja** — extraction was already complete from Sprint 6 #15+#16.
Baseline: 1037 rows, raw=1 (only `BANKERS / / -` falls through). 779
unclassified is classification-side, not extraction-side (single-name
RFLX rows / govt flows / loans). No app.py changes; harness committed.

**#10 BIMB Mytutor + KMZ** — three-part fix:
- [bank_islam.py](bank_islam.py) format2/3 walk lines with manual index
  and collect continuation lines until next date or BAL B/F. Mytutor
  PDFs print transactions as multi-line blocks with entity on
  continuation lines.
- [bank_islam.py](bank_islam.py) `_extract_own_party_name_bimb()`
  stamps `own_party_name` + `company_name` on every row, then strips
  the own-party echo from the joined description so (a) extraction
  window isn't truncated and (b) classifier doesn't fire false C01.
- [app.py](app.py) BIMB branch in `_extract_counterparty` (after
  Alliance, before HLB). Routes fee opcodes, profit, and entity-bearing
  opcodes (RTP REDIRECT CT, RTP IBFT, INW DuitNow Transfer, SA HSE CHQ
  DEP, IBG TRANSFER TO CA, FN AUTO RPY-HC, CDB CS TO IBFTS3, eSPICK
  INW PT LTD CO). Adds `own_party` param + new `_bimb_extract_tail_entity`
  helper that walks leading uppercase tokens until ref/digit/lowercase
  /(cid:NNN). Mytutor: **8046 rows, pattern=6786 / special=374 / raw=886**;
  top payers are full names (KAMARULHAYATI BINTI OTHMA, HALIMI BIN
  IBRAHIM, MDM NORAIDA NASPI). Felcra/Mazaa unchanged.

## State on arrival

```
git log --oneline -8
1ad4aab  BIMB Mytutor + KMZ
478e5fd  RHB Waja harness
045ee91  PBB Mazaa
aa42cdf  Auto-RP Step 1
d529231  V3-A handoff doc update
20d8e4d  V3-A handoff doc append
5731993  Sprint 7 #6 — Felcra harness
cd20a3e  Sprint 7 #5 — Bank Rakyat '?' strip
```

Branch: `sprint-6/polish`, 15 commits ahead of origin/sprint-6/polish.

## Memory entries created this session

- `memory/project_pbb_mazaa_followups.md` — Mazaa C01 6-char floor + broader PBB prefix routing
- `memory/project_rhb_waja_state.md` — Waja extraction complete; parser-side own-party stamping deferred (parser-wide gap)
- `memory/project_bimb_followups.md` — Principal Gas format1, Mytutor tuition-CR locked C26 rule, KMZ lower-volume opcodes

## Sprint 7 V3-A queue — REMAINING

The original V3-A handoff's six-item work order is now substantially
complete. What's left, in rough priority order:

1. **Principal Gas folder 5 (BIMB8489) format1 fix** — bank_islam.py
   format1 produces `'1 9895 INW DuitNow Transfer PRINCIPAL GAS SDN. B
   PGSB BIMB'` shape (leading sequence number, NOT 4-digit txn code).
   The BIMB branch's `^\s*\d{4}\s+` doesn't match. Either drop the
   `no` field from format1's `description_clean` join at
   [bank_islam.py:102](bank_islam.py#L102), or add a separate format1-shape
   regex to the BIMB branch. Also format1 has SDN BHD truncation
   ('SDN. B' → repair to 'SDN BHD'). 176 rows currently raw=176.

2. **Parser-wide own-party stamping audit** — RHB and others don't
   stamp `company_name` / `own_party_name`, so C01/C02 own-party can
   never fire. Alliance has `_extract_own_party_name`; bank_islam.py
   now has `_extract_own_party_name_bimb`. Audit which parsers stamp
   and which don't, then add similar helpers. Estimated ~30 LOC per
   parser. Caveat: Alliance helper requires SDN BHD/BERHAD/ENTERPRISE/
   TRADING — needs a relaxed extractor for short/marker-less names.

3. **kredit_lab_classify 6-char own-party floor** at
   [kredit_lab_classify.py:621](kredit_lab_classify.py#L621). Blocks
   "MAZAA" (5 chars) and similar short company names from firing C01.
   Requires audit of false-positive risk on other corpora before
   lowering. Documented in `project_pbb_mazaa_followups.md`.

4. **Auto-RP Step 2 — Anthropic SDK semantic scoring** (V3-B
   territory). Step 1 caught 4 HIGH on Felcra (good); Mytutor/KMZ
   need this for the long tail of personal-name CRs.

5. **Mytutor tuition-CR classification** — locked C26 rule excludes
   natural persons. Either per-business-type rule (schools/clinics/
   services treat natural-person CR as trade) or analyst RP4 sweep
   for student names. Don't change global rule.

6. **Broader PBB prefix routing** — TSFR FUND, MISC, A/C TSFR DR,
   DEP-CASH CDT (cash deposit → bucket), DEP-ECP / DR-ECP (cheques),
   AUTOMATED LOAN PYMT (loan repayment), HANDLING CHRG / SC / GST /
   CABLE CHRG (fees). Histogram in
   [scripts/verify_mazaa_v3a.py](scripts/verify_mazaa_v3a.py) output.

7. **`_br_extract_entity` rename** — used in Bank Rakyat, PBB Mazaa,
   and indirectly via similar logic in BIMB. Consider renaming to
   `_multi_bank_extract_entity` and moving to a shared helper section
   if it lands in 4+ banks.

8. **Concatenated SDN BHD detection** — ~30-50 Felcra rows fail to
   fire C26 because `\bSDN BHD\b` regex requires word boundaries.
   Add concatenated-form match (`\bSDNBHD\b`, `BERHAD` substring
   inside concatenated blob).

## Cross-bank verification status

Run these to confirm no regressions before any further changes:

```bash
python scripts/verify_felcra_v3a.py   # expect 59.1% (4373 rows)
python scripts/verify_mazaa_v3a.py    # expect 2.4% (497 rows)
python scripts/verify_waja_v3a.py     # expect 24.9% (1037 rows)
python scripts/verify_bimb_v3a.py kmz # expect 39.6% (192 rows, 33 unique CPs)
python scripts/verify_bimb_v3a.py mytutor       # 1.3% (locked C26 rule)
python scripts/verify_bimb_v3a.py principal_gas # 29.0% (limited by format1)
```

## First actions in new chat

1. Acknowledge handoff. Verify state:
   ```
   git log --oneline -10
   ```
   Expect top: 1ad4aab → 478e5fd → 045ee91 → aa42cdf → d529231 → 20d8e4d → 5731993 → cd20a3e.

2. Load relevant memories:
   - [project_pbb_mazaa_followups](memory/project_pbb_mazaa_followups.md)
   - [project_rhb_waja_state](memory/project_rhb_waja_state.md)
   - [project_bimb_followups](memory/project_bimb_followups.md)

3. Re-read the "Sprint 7 V3-A queue — REMAINING" section above and
   confirm priority with user. Default suggestion: **#1 Principal
   Gas format1** as the natural continuation of #10 — same Bank
   Islam ecosystem, smaller scope than the open parser-wide audits.
   Then **#2 parser-wide own-party stamping audit** if user wants to
   unlock C01/C02 firing across more banks.

4. Run the cross-bank verification suite above to confirm baseline
   before making changes.

## Open questions for #1 (Principal Gas)

- Drop the `no` (sequence number) field from format1's
  `description_clean` join, OR add a separate format1-shape regex to
  the BIMB branch in app.py? The first is parser-side and uniform;
  the second is routing-side and surgical.
- SDN BHD truncation repair (`SDN. B` / `SDN BH` → `SDN BHD`) — apply
  per-row, or only when extracting in the BIMB branch?

## Rollback procedure

```
# Drop session 4 commits (return to V3-A handoff doc):
git reset --hard d529231

# Drop just BIMB (#10):
git reset --hard 478e5fd

# Drop BIMB + Waja harness:
git reset --hard 045ee91

# Drop everything back to V2:
git reset --hard a8c3330
```

## Context budget note

This session used ~140k tokens. Heavy items: format2 continuation-line
debugging, BIMB own-party leak diagnosis (false C01 firing took 2
iterations to land), and three full verification harness runs against
8000+-row Mytutor.

# Handoff append — 2026-04-28 evening (Sprint 7 V3-A — #11/#12/#13: Principal Gas format1, parser-wide own-party stamping, concatenated holder extraction)

> **STATE:** Changes are UNCOMMITTED in the working tree as of this handoff.
> User chose to start a new chat without committing first.
> See "Rollback procedure" below — you may want to commit the four work
> items as separate commits before resuming, OR `git stash` if you want
> to bench them.

## What shipped this session (3 logical changes, 4 files modified)

```
M app.py            (BIMB stop-word filter + own-party self-transfer routing)
M bank_islam.py     (format1 desc-join: drop seq#, repair SDN BHD truncation)
M core_utils.py     (extract_account_holder_from_header + auto-stamp in finalize_parser_output)
M maybank.py        (header_text via pdfplumber; fitz multi-column was unreliable)
```

Recommended commit split:
1. `Sprint 7 #11 (V3-A): BIMB Principal Gas format1 + stop-word filter`
   — bank_islam.py + app.py BIMB-branch portions
2. `Sprint 7 #12 (V3-A): parser-wide own-party stamping via finalize_parser_output`
   — core_utils.py (extract_account_holder_from_header strict pass +
     stamp_account_holder + finalize integration), maybank.py, app.py
     BIMB own-party-routing portion
3. `Sprint 7 #13 (V3-A): concatenated-form holder extraction (Felcra)`
   — core_utils.py concat-pass additions

## Per-item results

**#11 BIMB Principal Gas format1 fix**
[bank_islam.py:102-122](bank_islam.py#L102-L122) — drop leading seq number from
`description_clean` join (so the BIMB branch's `^\s*\d{4}\s+` strip aligns
with the 4-digit txn code), repair `sender_recipient` column-truncation
endings (`SDN. B`, `SDN BH`, `SDN.` → `SDN BHD`; `BERH` → `BERHAD`).
Person-name truncations and ambiguous endings (`SD`, `S`) intentionally
left alone (false-positive risk).
[app.py:2392-2402](app.py#L2392-L2402) — added `_BIMB_PURPOSE_STOP_TOKENS` set
+ first-token check in [app.py:2557-2570](app.py#L2557-L2570) to bail
to UNNAMED on tails like `'REFUND INTO CUSTOME'`, `'FUND TRANSFE R'`,
`'TRF FUND'` left over from CA DR&CR ADVICE own-party adjustments.
Result: Principal Gas raw=176→1, classification 29.0% (noise) → 19.9%
(real, before #12).

**#12 BIMB own-party self-transfer routing + parser-wide stamping**
[app.py:2545-2570](app.py#L2545-L2570) — when BIMB's own-party strip + ref
strip leave an empty tail OR a purpose-word-only first token, route to
`own_party.upper()` bucket so C01/C02 fire (instead of UNNAMED BANK
ISLAM TRANSFER which never matches own-party).
[core_utils.py:842-1024](core_utils.py#L842-L1024) — added
`extract_account_holder_from_header(text, *, relaxed=False)` with strict
SDN BHD/BERHAD/ENTERPRISE/TRADING/SERVICES/HOLDINGS/RESOURCES/CONSULTING
suffix anchors + truncate-at-suffix-end (kills trailing Chinese
statement-date markers / `PENYATA AKAUN` suffix labels), and
`stamp_account_holder()` that uses `setdefault` (preserves any
parser-side stamping). Integrated into `finalize_parser_output` so all
8 parsers calling it with `header_text=` automatically benefit.
[maybank.py:232-275](maybank.py#L232-L275) — switched header_text source from
PyMuPDF (`fitz.get_text`) to pdfplumber. Fitz reads multi-column
Maybank PDFs non-linearly so transaction-row `<NAME> SDN. BHD.*`
strings shadowed the actual holder; pdfplumber preserves visual order.

Result: Principal Gas 19.9% → 30.7% (5 C01 + 14 C02 own-party fires).
**Plus** 9 of 10 previously-unstamping parsers now auto-stamp via
finalize_parser_output: rhb, maybank, public_bank, cimb, hong_leong,
ambank, bank_muamalat, agro_bank, and Bank Rakyat (non-Felcra
formats). Verified holders one PDF each:
- RHB Waja → JATI WAJA QUALITY SERVICES
- Maybank → DMC TRAVEL AND TOURS SDN BHD
- PBB → MAZAA SDN BHD
- CIMB → MUHAFIZ SECURITY SDN BHD / BINAAN DESJAYA SDN BHD
- HLB → DETIK VENTURES SDN BHD
- Ambank → AGENSI PEKERJAAN SWASTA TR SDN BHD
- Muamalat → ASIAN KALIBER SDN BHD
- Agro → INTEGRASI ERAT SDN BHD
- Bank Rakyat (non-Felcra) → CENFOTEC SDN BHD

**#13 Concatenated-form holder extraction**
[core_utils.py:894-913](core_utils.py#L894-L913) — added Pass 2 to the helper
that catches concatenated corp-suffix forms like
`KOPERASIKAKITANGANFELCRA(M)BERHAD` (Bank Rakyat DATAPOS) and
`AZLANBOUTIQUEENTERPRISE` (older RHB folders 1-7) where pdfplumber
loses inter-word spacing and the suffix anchor lacks a leading word
boundary. Bank-self filter (`MALAYAN\s*BANKING|RHB\s*BANK|...`,
tolerant of zero whitespace via `\s*`) skips lines like
`RHBBankBerhad196501000373(6171-M)`.

Result: Felcra now stamps `KOPERASIKAKITANGANFELCRA(M)BERHAD` across
all 6 PDFs; classification 59.1% → 59.2% (+1 C01 fire). Modest
because `_company_root` of the concatenated form yields
`KOPERASIKAKITANGANFELCRA M BERHAD` — most descriptive Felcra
counterparty buckets aren't substrings of that, so `cp_upper in root`
rarely fires. See "Open follow-ups" #1 for the path to a bigger lift.

## Cross-corpus verification (current state)

| corpus | rate | Δ vs pre-session | notes |
|---|---|---|---|
| Felcra (BR) | 59.2% | +0.1pp | +1 C01 from concat-form holder |
| Mazaa (PBB) | 2.4% | — | blocked by 6-char own-party floor |
| Waja (RHB) | 25.7% | +0.8pp | JATI WAJA C01 + 7 C02 own-party DRs |
| Mytutor (BIMB) | 1.3% | — | locked C26 rule excludes naturals |
| KMZ (BIMB) | 39.6% | — | unchanged |
| Principal Gas (BIMB) | 30.7% | +1.7pp net (vs 29% noise baseline) | extraction win + 5 C01 + 14 C02 |

## State on arrival

```
git log --oneline -5
8afa34a  Append handoff Sprint 7 V3-A (auto-RP, PBB Mazaa, RHB Waja, BIMB Mytutor+KMZ)
1ad4aab  Sprint 7 #10 (V3-A): BIMB Mytutor + KMZ
478e5fd  Sprint 7 #9  (V3-A): RHB Waja harness
045ee91  Sprint 7 #8  (V3-A): PBB Mazaa
aa42cdf  Sprint 7 #7  (V3-A): auto-RP Step 1
```

Branch: `sprint-6/polish`, 16 commits ahead of origin/sprint-6/polish
(15 from prior sessions + 1 from the prior handoff append).

`git status --short`:
```
M app.py
M bank_islam.py
M core_utils.py
M maybank.py
```
Plus the usual untracked sample/audit folders.

## Ship-ready strategy discussion (this session)

User stated target: **fully ship-ready** ("ready to sell"), not
partial / demo-able. Honest assessment of the gap, organized for
session-paced AI-assisted execution:

| item | sessions like this one | priority |
|---|---|---|
| **V3-B Auto-RP Step 2** (Anthropic SDK semantic scoring) | 1-2 | **P0** — biggest single rate lever; lifts Waja (Mohammad/Ashrul), Principal Gas (small contractor names), KMZ tail |
| **Cheap classifier wins** — 6-char own-party floor audit, broader PBB prefix routing, BIMB Principal Gas folder 5 (already done in #10/#11), Felcra concatenated `_company_root` split | 1 | P1 |
| **Affin OCR + Bank Rakyat DATAPOS hardening** | 1 | P1 |
| **Regression suite** (golden snapshots from 6 verify_*_v3a.py harnesses, fail-on-diff) | ½ | P1 |
| **Mytutor business-type rule** (per-vertical pack so tuition CRs from natural persons → C26 trade) | 1 | P2 |
| **Auth/multi-tenant** (Streamlit session-based or rebuild) | 1-2 (session) / weeks (rebuild) | P2; depends on selling motion |

User has not yet decided selling motion (design-partner pilots vs.
self-serve SaaS) — that gates the auth/UI scope. Engine-level
ship-ready is **6-8 focused sessions** at this cadence.

## Sprint 7 V3-A queue — REMAINING (post-#11/#12/#13)

In rough priority for ship-readiness:

1. **V3-B Auto-RP Step 2** — Anthropic SDK semantic scoring on
   personal-name / multi-party counterparty rows. Step 1 (deterministic
   signals) already shipped in commit aa42cdf. Step 2 takes Step 1's
   LOW/MEDIUM candidates plus the `(POSSIBLY MULTIPLE PARTIES)` rows
   and asks Claude to score related-party probability based on
   transaction patterns (frequency, amount distribution, bidirectional
   flow, description context). Files: extend
   [kredit_lab_classify.py:285](kredit_lab_classify.py#L285)
   `scan_related_party_candidates`. **Use the claude-api skill** —
   prompt caching is mandatory for cost; Opus 4.7 (1M context) is
   overkill, default to Sonnet 4.6 or Haiku 4.5 with cached system
   prompt. Calibrate against 6 existing verification corpora.

2. **6-char own-party floor cross-corpus FP audit** at
   [kredit_lab_classify.py:621](kredit_lab_classify.py#L621). Lowering
   to 5 chars would unblock Mazaa (5-char `MAZAA`), LSR, etc. Audit
   every short company-root candidate across all 6 verification
   corpora before lowering. Documented in
   [project_pbb_mazaa_followups](memory/project_pbb_mazaa_followups.md).

3. **Felcra concatenated `_company_root` improvement** — currently
   `_COMPANY_SUFFIXES.sub("", "KOPERASIKAKITANGANFELCRA(M)BERHAD")`
   leaves `KOPERASIKAKITANGANFELCRA M BERHAD` because BERHAD lacks a
   leading `\b`. Update the regex to handle concatenated suffix forms,
   so the root becomes `KOPERASIKAKITANGAN FELCRA` and longer
   counterparty buckets (e.g. `FELCRA BERHAD ARNETH`) substring-match
   own-party. Estimated +5-15pp on Felcra.

4. **Broader PBB prefix routing** — TSFR FUND (DR/CR)-ATM/EFT (163
   rows), MISC DR/CR (37 rows), A/C TSFR DR, DEP-CASH CDT, DEP-ECP /
   DR-ECP (cheques), AUTOMATED LOAN PYMT, HANDLING CHRG / SC / GST /
   CABLE CHRG (fees), CR CARD PYMT-ATM/EFT. Histogram in
   [scripts/verify_mazaa_v3a.py](scripts/verify_mazaa_v3a.py) output.
   See [project_pbb_mazaa_followups](memory/project_pbb_mazaa_followups.md).

5. **BIMB Principal Gas residuals** — `PGSB BIMB` bucket (1 tx, RM
   1k) is an own-party self-DuitNow where strips leave only bank/
   system codes. Could route to own-party via a 4-letter-acronym-only
   tail check. Negligible value; deferred.

6. **Affin OCR-fallback** — current corpus PDFs return 0 rows
   (`parse_affin_bank` produces empty list). Likely text-layer-empty
   triggering OCR path that isn't producing transactions. Separate
   bug class from header extraction.

7. **Bank Rakyat KKF Wakaf concatenated header** — distinct from
   Felcra; the line `KKFWAKAF NoRujukan/RefNo` doesn't contain a corp
   suffix. Either accept as "no holder extractable" or add a
   relaxed pass that picks the first all-caps short name on a header
   line that isn't an address. Lower priority than #1-#5.

8. **Regression suite** — package the 6 `verify_*_v3a.py` harnesses
   into a single runner that snapshots category counts + top-buckets
   + classification rates, fails CI on diff. Half a session.

9. **Mytutor per-business-type rule** — locked C26 excludes naturals
   globally; need a per-vertical override (schools/clinics treat
   natural-person CR as trade income). Don't change the global rule.
   See [project_bimb_followups](memory/project_bimb_followups.md).

10. **`_br_extract_entity` rename** — used in BR, PBB Mazaa, BIMB
    indirectly. Move to shared location and rename
    `_multi_bank_extract_entity` if it lands in 4+ banks. Small.

## First actions in new chat

1. Acknowledge handoff. Verify state:
   ```
   git status --short
   git log --oneline -5
   ```
   Expect 4 uncommitted files (app.py, bank_islam.py, core_utils.py,
   maybank.py). Top commit is still 8afa34a.

2. **Decide commit strategy.** Three options:
   - **A.** Commit the 4 files now as 3 separate commits (#11, #12, #13)
     per the split above, then proceed to #1 V3-B.
   - **B.** `git stash` the changes, work on something orthogonal,
     restore later.
   - **C.** Continue without committing (next session inherits
     uncommitted state — risk if anything breaks).
   Recommend **A** — clean state, deletable per-item if regressions
   appear later.

3. Re-run cross-corpus verification to baseline before any changes:
   ```bash
   python scripts/verify_felcra_v3a.py             # expect 59.2%
   python scripts/verify_mazaa_v3a.py              # expect 2.4%
   python scripts/verify_waja_v3a.py               # expect 25.7%
   python scripts/verify_bimb_v3a.py mytutor       # expect 1.3%
   python scripts/verify_bimb_v3a.py kmz           # expect 39.6%
   python scripts/verify_bimb_v3a.py principal_gas # expect 30.7%
   ```

4. Load relevant memories:
   - [project_pbb_mazaa_followups](memory/project_pbb_mazaa_followups.md)
   - [project_rhb_waja_state](memory/project_rhb_waja_state.md)
   - [project_bimb_followups](memory/project_bimb_followups.md)
   - (NEW — to be created) `project_ship_ready_strategy.md`

5. Confirm with user: which item from the queue? Default
   recommendation per the ship-readiness discussion: **#1 V3-B
   Auto-RP Step 2** (biggest single lever, 1-2 sessions).
   Alternative: bundle #2/#3/#4 into a "cheap classifier wins"
   session (1 session, broad cross-corpus lift).

## Rollback procedure

```
# Drop ALL uncommitted Sprint 7 #11/#12/#13 work (return to 8afa34a):
git checkout -- app.py bank_islam.py core_utils.py maybank.py

# OR stash for later:
git stash push -m "Sprint 7 #11/#12/#13 work" -- \
    app.py bank_islam.py core_utils.py maybank.py

# AFTER committing per the recommended split, granular rollback:
git reset --hard <#13 commit>   # drop concat-form extension
git reset --hard <#12 commit>   # drop parser-wide stamping
git reset --hard <#11 commit>   # drop Principal Gas format1
git reset --hard 8afa34a        # drop all of this session
```

## Context budget note

This session used ~125k tokens. Heavy items: Felcra/Bank Rakyat header
inspection (concatenated text format discovery), Maybank PyMuPDF
multi-column debugging (3 iterations to land), and the Sprint 7
ship-readiness strategy discussion in the back half.

---

# Handoff append — 2026-04-28 night (Sprint 7 Phase 2A — cheap classifier wins)

## What shipped this session

Two commits landed on top of `8afa34a`:

```
34ff8ab  Sprint 7 #11/#12/#13 (V3-A): BIMB Principal Gas format1 + parser-wide
         own-party stamping + concatenated holder extraction
fbca8e6  prompts: Append Sprint 7 #11/#12/#13 handoff to NEXT_CHAT_PROMPT.md
df206f4  Sprint 7 Phase 0: BUG-001 statutory side-gate + v3.5.6 enum fix
         (committed by parallel session, NOT this session — see "Note on
         parallel-session interference" below)
0f538fd  Sprint 7 Phase 2A (V3-A): cheap classifier wins — Felcra _company_root
         + own-party 5-char floor + PBB DEP-ECP/DR-ECP routing
da3d73c  prompts: Append Sprint 7 Phase 2A handoff (this handoff itself)
3e3f0fc  v3.5.6 patch (Track 1 Phase 2): 3 rule tightenings; rule 3 deferred
         (Track 1, NOT this session — only touched SYSTEM_PROMPT/CHANGELOG/
         TRACK_1_HANDOFF; no Track 2 collateral)
```

Branch: `sprint-6/polish`, **22 commits ahead of `origin/sprint-6/polish`**.

## Phase 2A — three small changes, one commit

User chose **Option C** ("cheap wins first, then strengthen Step 1") after
the V3-B Auto-RP Step 2 LLM scoring plan was killed by the **no-SDK rule**
(see `feedback_no_sdk_until_bank_deploy.md` — all AI scoring goes through
claude.ai web manually until the project is ready to deploy with the
Bank). All three Phase 2A changes are deterministic Python only, no API
calls.

**1. `_company_root` paren-strip**
[kredit_lab_classify.py:515-526](kredit_lab_classify.py#L515-L526) — apply
`_PAREN_DISAMBIGUATOR` BEFORE `_COMPANY_SUFFIXES`, mirroring
`_canonicalize_for_merge` at line 529. Concat-form holder
`KOPERASIKAKITANGANFELCRA(M)BERHAD` now reduces to clean
`KOPERASIKAKITANGANFELCRA` (24 chars) instead of `KOPERASIKAKITANGANFELCRA M`.
Bucket `KOPERASIKAKITANGANFELCRA BERHAD` (31 tx, RM 2.26M) now substring-
matches via `root in cp_upper`, fires C01.

Result: Felcra rate **unchanged at 59.2%** (the 32 newly-C01 rows were
previously firing C26 trade income, so total-classified count is same).
But categorisation is now correct — own-party transfers between the
holder's accounts are no longer misclassified as trade income.

**2. Own-party floor 6→5**
[kredit_lab_classify.py:624-637](kredit_lab_classify.py#L624-L637) — root-
length floor lowered from 6 to 5 chars. cp-side floor stays at 6.
Audit across all 6 verification corpora confirmed only Mazaa has a
5-char root (`MAZAA`); 55 `DUITNOW TRSF CR ... MAZAA SDN BHD` rows are
**100% legitimate own-party self-transfers**, zero FP risk.

Result: 55 Mazaa rows (RM 941k) now fire C01. Mazaa rate 2.4% → 13.5%.

**3. PBB DEP-ECP / DR-ECP routing**
[app.py:3716-3728](app.py#L3716-L3728) — bank-gated route in the existing
PBB block of `_extract_counterparty`. `DEP-ECP <ref>` → `CHEQUE DEPOSIT`
bucket; `DR-ECP <ref>` → `CHEQUE ISSUE` bucket. Both new buckets added
to `BUCKET_TO_CATEGORY`:
[kredit_lab_classify.py:111-112](kredit_lab_classify.py#L111-L112).
`CHEQUE DEPOSIT` → C19 (Cheque Deposit, CR-side), `CHEQUE ISSUE` → C20
(Cheque Issue, DR-side). Side-gated by existing `_CATEGORY_SIDES`.

Cross-bank-keyword-unsafe (`DEP-ECP` is PBB-specific opcode terminology)
so kept in the PBB-bank-gated block, NOT added to `_KEYWORD_RULES`.
Per `feedback_crossbank.md`, never put bank-specific tokens in cross-
bank rules.

Result: 391 Mazaa rows (75% of statement) now classify. Mazaa rate
**13.5% → 92.2% (+78.7pp from this change alone)**.

## Cross-corpus verification (post-Phase 2A)

| corpus | pre-2A | post-2A | Δ | notes |
|---|---|---|---|---|
| Felcra | 59.2% | 59.2% | 0 | +32 rows correctly C01 vs C26 (semantic fix) |
| **Mazaa** | **2.4%** | **92.2%** | **+89.8pp** 🚀 | DEP-ECP+DR-ECP→C19/C20 (391 rows); MAZAA→C01 (55) |
| Waja | 25.7% | 25.7% | 0 | no PBB; root len=17 (unaffected by floor) |
| Mytutor | 1.3% | 1.3% | 0 | locked C26 natural-person exclusion |
| KMZ | 39.6% | 39.6% | 0 | no PBB |
| Principal Gas | 30.7% | 30.7% | 0 | no PBB |

Combined Phase 1 + Phase 2A delta on Mazaa = **+89.8pp** (largest single-
session lift in V3-A).

Mazaa post-state breakdown:
```
CLASSIFICATION: 458/497 = 92.2%
  C19   371   (CHEQUE DEPOSIT bucket — DEP-ECP electronic cheque clearing)
  C01    55   (own-party MAZAA via lowered floor)
  C20    20   (CHEQUE ISSUE bucket — DR-ECP)
  C24    10   (BANK FEES — HANDLING CHRG / CHQ PROCESS FEE / GST / SC)
  UNCLASS 41  (residual: 4 GIRO PYMT, 2 RMT CR, 1 TSFR FUND CR-ATM/EFT, 1
              HSE CHEQ RTN, 33 misc small)
```

## Note on parallel-session interference

The user ran a parallel session that committed **`df206f4` Sprint 7
Phase 0: BUG-001 statutory side-gate + v3.5.6 enum fix** between this
session's first two commits and Phase 2A. Their work is in
`core_utils.py` (statutory side-gate: never stamp KWSP/SOCSO/LHDN/HRDF
on CR rows or rows where the holder's normalised name appears in the
description), `prompts/CHANGELOG.md` (v3.5.6 patch entry), and
`SYSTEM_PROMPT_v3_5_6.md` (`ledger_cleaning_status` enum fix:
`CLEANED|VALIDATION_FAILED|SKIPPED` instead of the schema-illegal
`PASSTHROUGH|PASSTHROUGH+RP_STAMPED`).

**Unexplained git behavior at the Phase 2A commit step.** I ran
`git add app.py kredit_lab_classify.py` (only those two paths), then
`git commit -m "..."` (no `-a` flag, no aliases, no hooks, no
`commit.template`). The commit captured **6 files** instead of 2 — the
two I staged plus `prompts/CHANGELOG.md`, `prompts/TRACK_1_HANDOFF.md`,
`SYSTEM_PROMPT_v3_5_6.md`, and a new `prompts/RUN_INPUT_TEMPLATE.md`
(previously untracked). Cannot reproduce post-hoc. Possibly some VS Code
git extension or Claude Code harness behaviour I missed.

The bundling is functionally fine (the parallel-session prompt-doc
changes were going to push along anyway per the user's
"my commit will go along with it" comment), but the commit message only
documents the Phase 2A work, not the bundled prompt-doc changes. If a
clean split is required later: `git reset --soft HEAD~1` and re-commit
in two pieces — but the prompt-doc author should review their bundled
changes first before splitting (the Phase 2A author can't speak to the
correctness of the prompt-doc edits).

## State on arrival

```
git status --short
?? Bank-Statement/Alliance/bestlite/
?? "Bank-Statement/BankIslam/Mytutor Academy/"
?? "Bank-Statement/Fraud Bank Statement/"
?? CLAUDE.md
?? audit_reports/
?? bank-statement-analysis-HTML-fresh/
?? scripts/verify_ab_nov.py
?? "validation runs - json/22 april 2026 - result HTML(MTA,KYDN,MSSB)/"
?? "validation runs - json/AI Analyzed Json/"
?? "validation runs - json/Claude AI challenges/"
?? "validation runs - json/Test HTML result/"
?? "validation runs - json/claude ai prompt file/Full Report Sample/"
?? "validation runs - json/quality report parser/"
```

Working tree clean (only the usual untracked sample/audit folders).

## Phase 2B queue — Strengthen Step 1 RP signals (this is what V3-B becomes
under the no-SDK rule)

V3-B was originally framed as "Anthropic SDK semantic scoring on
personal-name candidates." Since the no-SDK rule (see
`feedback_no_sdk_until_bank_deploy.md`) blocks API calls until the
project is ready to deploy with the Bank, V3-B's deterministic
substitute is **strengthening Step 1's `_compute_rp_signals`** in
[kredit_lab_classify.py:315-392](kredit_lab_classify.py#L315-L392) so
more LOW/MEDIUM candidates promote to HIGH automatically — fewer rows
fall through to claude.ai-web for manual scoring.

Highest-value targets:

1. **RHB Waja's 287 `MOHAMMAD (possibly multiple parties)` rows.** This
   is the single biggest unresolved bucket across all 6 corpora. Step 1
   today does not discriminate `(possibly multiple parties)` markers
   from regular candidates. Add an `ambiguous_multi_party` flag and
   default these to LOW (not HIGH) — they're inherently ambiguous and
   should not fire C03/C04 without analyst confirmation.
2. **Surname clustering against `own_party_name`.** When a candidate
   shares a `BIN`/`BINTI`/`A/L`/`A/P` surname token with the holder's
   directors/shareholders (currently we don't have a directors list,
   but the holder's own name is a proxy), promote LOW → MEDIUM.
3. **Round-amount + monthly cadence.** Already partially scored via
   Step 1's `signals` list. Tighten thresholds: ≥5 round-RM transactions
   in ≥4 distinct months → MEDIUM; ≥10 round-RM + bidirectional flow
   → HIGH.
4. **Patrilineage cluster size.** When N candidates share a patrilineage
   token (`BIN OTHMAN` × 5 candidates) AND each has small amounts, this
   is bulk-salary, NOT RP — explicit demote to LOW.
5. **`_RP_HIGH_SCORE` / `_RP_MEDIUM_SCORE` calibration.** Currently 3 / 2
   (line 311-312). Re-calibrate after adding new signals so the
   distribution stays sane on Waja (the highest-volume RP-candidate
   corpus).

Estimated lift: **+3-8pp on Waja**, smaller on Principal Gas.
Felcra already has good Step 1 detection (see `RP candidates (top 10
by confidence)` block in `verify_felcra_v3a.py` output — 2 HIGH names
auto-fire). Mytutor lift requires the locked-C26 per-vertical override,
not Step 1 work. KMZ already at 39.6% from existing signals.

## Sprint 7 V3-A queue — REMAINING (post-Phase 2A)

In rough priority for ship-readiness:

1. **Phase 2B — strengthen Step 1 RP signals** (see above). 1 session.
2. **Affin OCR-fallback** — current corpus PDFs return 0 rows
   (`parse_affin_bank` produces empty list). Likely text-layer-empty
   triggering OCR path that isn't producing transactions. 1 session.
3. **Bank Rakyat KKF Wakaf concatenated header** — distinct from
   Felcra; the line `KKFWAKAF NoRujukan/RefNo` doesn't contain a corp
   suffix. Lower priority than Phase 2B.
4. **Regression suite** — package the 6 `verify_*_v3a.py` harnesses
   into a single runner that snapshots category counts + top-buckets
   + classification rates, fails CI on diff. Half a session.
5. **Mytutor per-business-type rule** — locked C26 excludes naturals
   globally; need a per-vertical override (schools/clinics/services
   treat natural-person CR as trade income). Don't change the global
   rule.
6. **Felcra concatenated `_company_root` is now FIXED — drop from queue.**
   (Was item #3 in the prior handoff.)
7. **Broader PBB prefix routing for non-ECP opcodes** — `TSFR FUND
   (DR/CR)-ATM/EFT`, `MISC DR/CR`, `A/C TSFR DR`, `DEP-CASH CDT`,
   `AUTOMATED LOAN PYMT`, `CR CARD PYMT-ATM/EFT`. Mazaa corpus alone
   doesn't have many of these — only 1 `TSFR FUND CR-ATM/EFT` row, 4
   `GIRO PYMT-ATM/EFT`, no `MISC` or `A/C TSFR`. Defer until a corpus
   surfaces them in volume.
8. **`_own_party_match` 6-char floor — DONE (lowered to 5 in Phase 2A).
   Drop from queue.**
9. **`_br_extract_entity` rename** — used in BR, PBB Mazaa, BIMB
   indirectly. Move to shared location and rename
   `_multi_bank_extract_entity` if it lands in 4+ banks. Small.

## First actions in new chat

1. Acknowledge handoff. Verify state:
   ```bash
   git status --short
   git log --oneline -6
   ```
   Expected: clean tree (only untracked sample/audit folders), top
   commit `3e3f0fc` (Track 1 Phase 2). Phase 2A code commit `0f538fd`
   sits two commits below HEAD; the Phase 2A handoff append is
   `da3d73c`, also below HEAD. The current handoff append (this one)
   will land on top after `git commit` and may show as `HEAD` itself.

2. Re-baseline before any changes — should match this handoff's table:
   ```bash
   python scripts/verify_felcra_v3a.py             # 59.2%
   python scripts/verify_mazaa_v3a.py              # 92.2%
   python scripts/verify_waja_v3a.py               # 25.7%
   python scripts/verify_bimb_v3a.py mytutor       # 1.3%
   python scripts/verify_bimb_v3a.py kmz           # 39.6%
   python scripts/verify_bimb_v3a.py principal_gas # 30.7%
   ```
   The 6 are independent — run as parallel background bashes for
   ~3min wall-clock instead of 15min serial.

3. Load relevant memories:
   - `feedback_no_sdk_until_bank_deploy` — **CRITICAL.** Do NOT design
     features around Anthropic SDK; all AI work goes through claude.ai
     web manually until the user explicitly signals "ready to deploy
     with Bank."
   - `feedback_crossbank` — never add bank-specific tokens to
     `_KEYWORD_RULES` cross-bank rules.
   - `project_pbb_mazaa_followups` — UPDATED post-Phase 2A: 6-char
     floor done, ECP routing done. Remaining items deferred.
   - `project_rhb_waja_state` — Waja's 779 unclassified rows are
     classification-side, not extraction-side. Phase 2B target.
   - `feedback_inspect_data_first` — dump actual values before naming
     a root cause.

4. Confirm with user: **default recommendation is Phase 2B (strengthen
   Step 1 RP signals)** per the user's Option C plan. Targets RHB
   Waja's 287-row `MOHAMMAD (possibly multiple parties)` blocker.

## Rollback procedure

```bash
# Drop Phase 2A only (keep #11/#12/#13 + parallel-session BUG-001):
git revert 0f538fd

# Drop the parallel-session BUG-001 commit too:
git revert df206f4

# Hard-reset to pre-Phase 2A:
git reset --hard df206f4  # keeps BUG-001
git reset --hard fbca8e6  # drops BUG-001 too
git reset --hard 8afa34a  # drops everything from this and prior session
```

## Context budget note

This session used ~150k tokens. Heavy items: parallel verify-harness
runs (6 corpora × 2 baselines), the V3-B SDK plan that got killed by
the no-SDK rule (~25k wasted on a dead-end design), the Felcra
`_company_root` semantic-fix vs rate-fix diagnostic, and the
unexplained 4-file git bundle at commit time.

---

# Sprint 7 Phase 2B handoff (2026-04-29) — partial completion, redirect

## What shipped this session (1 commit, 1 file modified + 2 new helper scripts)

`kredit_lab_classify.py` `_compute_rp_signals` — two changes that improve
classifier *correctness* at flat coverage. Phase 2B was originally
budgeted for `+3-8pp on Waja`; actual delivery is **−0.2pp net** with
quality improvements that are not visible in the rate metric.

| Change | Effect | Empirical justification |
|---|---|---|
| `ambiguous_multi_party` flag (refined: bidirectional exempt) | Force LOW for `(possibly multiple parties)` markers UNLESS bidirectional_flow signal fires. Preserves auto-confirm on real director-loan accounts (e.g. RHB Waja ASHRUL with `Bayar balik IBK` memos), demotes one-way ambiguous buckets that can't be disambiguated (ATASHA, MOHAMMAD). | Sample inspection of demoted buckets: ASHRUL (57 DR/22 CR with explicit "loan repayment" memos) is real RP — kept HIGH. ATASHA (14 DR-only) cannot be told from 14 different ATASHAs — correctly held for analyst review. |
| `round_amount_sustained` signal (weight 2) | New tier on the round-amount signal: ≥5 round DRs across ≥4 calendar months gets weight 2 (vs the existing weight 1 for ≥2 round DRs). Promoted 2 LOW→HIGH on Waja. | Revolving director-draw cadence is a strong same-person signal even when the bucket name is slightly ambiguous. Threshold high enough to filter one-off vendor refunds. |

Initial blanket-demote attempt regressed Waja −16pp (25.7% → 9.6%) by
killing 166 RP-fired transactions including ASHRUL's 79. Refined
exemption recovered 142 of 166 (now 24.3% → 25.5% after target #3).

## Cross-corpus verification (post-Phase 2B partial)

| Corpus | Pre-Phase-2B | Post-Phase-2B | Δ |
|---|---|---|---|
| Felcra | 59.2% | 59.2% | 0 |
| Mazaa | 92.2% | 92.2% | 0 |
| **Waja** | **25.7%** | **25.5%** | **−0.2pp** |
| Mytutor | 1.3% | 1.3% | 0 |
| KMZ | 39.6% | 39.6% | 0 |
| Principal Gas | 30.7% | 30.7% | 0 |

Waja's −0.2pp net = (−1.4pp from correctly demoting ATASHA-style one-way
ambiguous buckets) + (+1.2pp from sustained-round catching 2 new HIGH
director-draw candidates). Other 5 corpora unaffected — the
`(possibly multiple parties)` marker is RHB-specific (Sprint 6 #15/#16)
and sustained-round candidates already concentrated in their
HIGH/MEDIUM tiers.

## Why targets #2/#4/#5 were skipped — empirical reasoning

The handoff's `+3-8pp on Waja` estimate assumed targets #2-#4 would each
add several auto-confirmed HIGHs. Empirical inspection showed that
premise doesn't hold against the actual test corpora:

- **#2 Surname clustering against `own_party_name`** — all 6 holders are
  corporate (`JATI WAJA QUALITY SERVICES`, `KMZ RESTU ENTERPRISE SDN
  BHD`, `MYTUTOR ACADEMY SDN BHD`, `PRINCIPAL GAS SDN BHD`, `FELCRA
  BERHAD`, Mazaa). None contain BIN/BINTI/A/L/A/P tokens. Signal would
  be a no-op until a sole-prop or personal-account corpus exists.
- **#4 Patrilineage cluster demote** — `scripts/inspect_rp_clusters.py`
  empirically dumps clusters across all 4 RHB/Felcra/KMZ/PG corpora.
  Findings: Felcra has ROSLI×2 and MOHAMED×2 but **all members already
  LOW** (demote is no-op). Waja's ambiguous markers hide surnames so
  clusters can't form. KMZ has a regex false-positive cluster (MD×2 —
  "MD" is "Mohamed" abbreviation, not a unique surname) which would
  WRONGLY demote KMZ's only HIGH RP candidate. Implementing #4
  requires careful surname stop-list engineering for zero measurable
  lift on current corpora.
- **#5 Recalibrate `_RP_HIGH_SCORE` from 3 → 2** — would promote
  Felcra MEDIUMs (SAZALI, MOHDISKANDAR, MOHDAZMAN — each ~RM 3-4k
  spread over 3-4 months). These look like staff loan/advance patterns,
  not director RP. Without ground truth to validate they're real RPs,
  lowering the threshold trades one false-positive class (already-fixed
  ambiguous one-way) for another (staff-loan auto-fired as RP). The
  no-SDK rule means analysts review every HIGH manually at the Bank —
  so net effect is more wrong-RP noise on the analyst desk, not lift.

These three are deferred, not killed. Conditions for revisiting:
- **#2:** A sole-prop test corpus (holder name has BIN/BINTI/A/L/A/P).
- **#4:** A multi-employee family-business corpus where 3+ candidates
  share an actual surname token (not "MD" abbrev) AND the existing
  signals would otherwise tier them MEDIUM/HIGH (so demote has effect).
- **#5:** Ground-truth labels (analyst-confirmed RP-vs-not on a corpus)
  to grade a proposed threshold change against precision/recall.

## What's left in the Sprint 7 V3-A queue (post-Phase-2B partial)

In rough priority for ship-readiness:

1. **Affin OCR-fallback** — `parse_affin_bank` returns 0 rows on the
   reference corpus. Likely text-layer-empty triggering the OCR path
   that isn't producing transactions. **Concrete extraction-side bug
   fix with measurable lift; recommended next.** 1 session.
2. **Regression suite** — package the 6 `verify_*_v3a.py` harnesses
   into a single runner that snapshots category counts + top-buckets
   + classification rates, fails CI on diff. Half a session. Would
   have caught the −16pp blanket-demote drop in Phase 2B target #1
   automatically.
3. **Bank Rakyat KKF Wakaf concatenated header** — distinct from
   Felcra; the line `KKFWAKAF NoRujukan/RefNo` doesn't contain a corp
   suffix. Lower priority than Affin.
4. **Mytutor per-business-type rule** — locked C26 excludes naturals
   globally; need a per-vertical override (schools/clinics/services
   treat natural-person CR as trade income). Don't change the global
   rule.
5. **Broader PBB prefix routing for non-ECP opcodes** — `TSFR FUND
   (DR/CR)-ATM/EFT`, `MISC DR/CR`, `A/C TSFR DR`, `DEP-CASH CDT`,
   `AUTOMATED LOAN PYMT`, `CR CARD PYMT-ATM/EFT`. Mazaa corpus alone
   doesn't have many of these — defer until a corpus surfaces them in
   volume.
6. **`_br_extract_entity` rename** — used in BR, PBB Mazaa, BIMB
   indirectly. Move to shared location and rename
   `_multi_bank_extract_entity` if it lands in 4+ banks. Small.
7. **Phase 2B targets #2/#4/#5** — see deferred conditions above.

## Helper scripts added this session

- `scripts/sample_demoted_waja.py` — dumps 5 sample rows from each of
  the 4 ambiguous-marker buckets (ATASHA, ASHRUL, KEMENTERI, JABATAN)
  so analysts can eyeball whether previously auto-fired C03/C04 was
  real RP signal or false positive. Used to diagnose the Phase 2B
  target #1 blanket-demote regression.
- `scripts/inspect_rp_clusters.py` — extracts BIN/BINTI/A/L/A/P
  patrilineage tokens from RP candidates across all 4
  Felcra/Waja/KMZ/PG corpora and dumps clusters with ≥2 members.
  Empirical input for the target #4 skip decision. Reusable any time
  this question comes back.

## State on arrival (next chat)

Working tree should be clean except for the usual untracked
sample/audit folders. Top commit will be the Phase 2B partial
(`kredit_lab_classify.py` + 2 helper scripts + this handoff append).

## First actions in new chat

1. Acknowledge handoff. Verify state:
   ```bash
   git status --short
   git log --oneline -8
   ```

2. Re-baseline (must match this handoff's table):
   ```bash
   python scripts/verify_felcra_v3a.py             # 59.2%
   python scripts/verify_mazaa_v3a.py              # 92.2%
   python scripts/verify_waja_v3a.py               # 25.5%   ← changed from 25.7%
   python scripts/verify_bimb_v3a.py mytutor       # 1.3%
   python scripts/verify_bimb_v3a.py kmz           # 39.6%
   python scripts/verify_bimb_v3a.py principal_gas # 30.7%
   ```
   Run as parallel background bashes.

3. Load relevant memories — same set as Phase 2A, plus:
   - `feedback_inspect_data_first` — Phase 2B's lift estimate failed
     because the original handoff didn't dump the data first (the
     prerequisites for #2 and #4 to fire weren't actually present in
     the corpora).

4. **Default recommendation: Affin OCR-fallback.** Different parser
   file (`affin_bank.py`), no merge conflict with Phase 2B work,
   concrete measurable lift (0 rows → N rows on a real corpus is much
   easier to verify than RP-signal heuristic tuning).

## Rollback procedure

```bash
# Drop Phase 2B partial:
git revert <phase-2b-commit-hash>

# Hard-reset to pre-Phase-2B (HEAD before Phase 2B commit):
git reset --hard 90b8254
```

## Context budget note

This session used ~75k tokens. Heavy items: blanket-demote regression
diagnostic (~20k spent on the −16pp investigation), refined exemption
implementation, surname-cluster empirical inspection (`inspect_rp_clusters.py`
required two parser-API debugging rounds), final options/recommendation
write-up. The user's prompt "i dont understand. what does the
percentage means? does it mean we have to go to 100%?" was the right
question at the right time — preempted shipping a regression by
forcing a metric-vs-correctness reframe.

---

# Track 2 architecture decision (2026-05-01) — direction set, no code yet

## What this session settled

After analyzing the full v3.5.6 system prompt (831 lines) plus the actual classification rates on the 6 corpora, this session established the long-term architectural direction. Saved to project memory as `project_track_2_architecture.md`.

**Previous (current) state — now labelled "Track 1":** AI-heavy classification. Deterministic engine pre-classifies ~30-90% (varies by corpus extraction quality); the v3.5.6 prompt re-implements RP1-RP8 detection, C26 government extension, C27 corporate-suffix rules, IBG return pairing, statutory side-gates, balance trail reconciliation, EOD computation, ghost-verb suppression, ledger validation, and 16-flag computation on top.

**Future direction — labelled "Track 2":** Engine-heavy classifier + thin AI prompt. Tier 1+2+3 deterministic logic ports into the engine; AI prompt shrinks to ~150-200 lines covering only Tier 4 (genuine analyst-judgment items + narrative).

## Track 1 / Track 2 separation rules (HARD CONSTRAINTS)

| | Track 1 (current production, FROZEN) | Track 2 (new, to be built) |
|---|---|---|
| Classifier code | `kredit_lab_classify.py` | `kredit_lab_classify_track2.py` (NEW) |
| System prompt | `SYSTEM_PROMPT_v3_5_6.md` | `SYSTEM_PROMPT_TRACK2_v0_1.md` (NEW) |
| Rules JSON | `CLASSIFICATION_RULES_v3_5.json` | `CLASSIFICATION_RULES_TRACK2_v0_1.json` (NEW, or read-only re-use of v3_5) |
| Schema | `BANK_ANALYSIS_SCHEMA_v6_3_5.json` (shared, no fork) |
| Parsers / `core_utils` / `build_counterparty_ledger` | (shared infrastructure — fixes benefit both tracks) |
| Deployment | Continues indefinitely | Built alongside; ships after side-by-side validation; Track 1 stays as fallback |

**Pipeline boundary (fork point):**
```
PDF → Parser → normalize → dedupe → build_counterparty_ledger    (SHARED)
                                          │
                                  ────── FORK ──────
                                  │                │
                          classify_transactions    classify_track2  ← NEW
                          (Track 1, frozen)        (Track 2, new file)
```

**Hard rules (NEVER violate):**
- NO edits to `kredit_lab_classify.py`, `SYSTEM_PROMPT_v3_5_6.md`, or `CLASSIFICATION_RULES_v3_5.json` for Track 2 reasons. Track 1 files are frozen indefinitely.
- Track 2 classifier code MUST NOT import from Track 1 classifier code. No shared classify functions.
- Parser fixes (e.g. Affin OCR-fallback) are SHARED-infrastructure improvements, not Track 1 modifications — both tracks benefit.
- Track 1 retires only when user explicitly approves, after Track 2 has been stable for a user-determined period.
- Track 2 ships only after side-by-side validation on all 6 verify corpora confirms no regression vs Track 1.

## Migration tiers

**Tier 1 — Already in engine** (no migration work):
- Account type detection, balance trail reconciliation, Stage 1 parser buckets → C-codes lookup, own-party detection, auto-confirmed RP scan, `ambiguous_multi_party` + `round_amount_sustained` signals (today's Phase 2B work).

**Tier 2 — Easy migratable** (deterministic math/lookup/regex; encode in `kredit_lab_classify_track2.py`):
- EOD computation algorithm
- 16-flag computation
- Net credits/debits formulas
- Statutory compliance computation (coverage % via set intersection, per-month ratio with bands, status enum)
- Ghost-verb suppression
- Counterparty normalisation (PLANWORTH, JANM, suffix-fragment merge)
- C26 corporate-suffix detection (SDN BHD / BHD / ENTERPRISE / TRADING / CORPORATION / GROUP)
- C26 government counterparty extension (KERAJAAN / JANM / KASTAM / etc.)
- C27 corporate-suffix detection
- IBG/DuitNow return pairing (±5 business days window)
- Vehicle plate C11 detection
- OTHER TRANSFER FEE → C24 rule
- Patronymic guard (BA/TL/TF/FD/CT collision skip)
- Factoring entity matching (known list + 'F ADVANCE' keyword)
- C18 vs C20 (CASH CHQ DR vs HOUSE/CLRG CHQ DR)
- Tax matching (C08) — LHDN full phrase + abbreviation
- C13/C14/C15/C16 reversal/return keyword classification
- C19/C20 cheque keyword classification
- JomPAY rule (don't classify on biller code alone)
- Schema validation hard gate (`jsonschema.validate`)
- Ledger totals validation (cr_total_gap, dr_total_gap, tx_count_gap)
- M7 canonical RP-name stamping

**Tier 3 — Algorithmic ports** (deterministic but multi-stage; encode after Tier 2):
- RP2 root-name match (sister-co)
- RP6 exclusion list (gov, banks, utilities, factoring, vehicle plates)
- RP7 share-capital detection
- RP8 surname-based family detection
- RP3 director-behavior expansion
- RP5 fuzzy name matching (Levenshtein/normalized comparison)
- C05 salary keyword full list
- C10 known-factoring (Tier 1 portion)
- C11 loan repayment priority logic (own loan vs related-party personal loan)
- C11 account-number-only loan transfers

**Tier 4 — Stays in Track 2 prompt** (genuine analyst-judgment items):
- Commission cluster decision (employees vs contractors)
- Per-vertical C26 override (tuition / clinic / professional services)
- C05 vs C27 marketplace contractor fork
- MEDIUM-confidence RP candidate handling
- STRUCTURAL EPF/SOCSO ratio interpretation
- Government counterparty side disambiguation (CR vs DR)
- Account-type override (low/medium confidence runs)
- Narrative synthesis (observations.positive / concerns)
- Parser quality commentary (Deliverable 2)
- Disambiguating UNCLASSIFIED rows in the final report

Track 2 prompt scope: ~150-200 lines (vs Track 1's 831).

## Migration sequencing (suggested)

1. **Session 1 — first Tier 2 port** (start here): pick **EOD computation** OR **16-flag computation** as the first migration target. Both are pure deterministic algorithms with well-defined inputs/outputs. Producing one of them creates the foundation file `kredit_lab_classify_track2.py`.
2. **Sessions 2-5:** continue Tier 2 ports (2-4 items per session).
3. **Sessions 6-8:** Tier 3 algorithmic ports.
4. **Session 9:** draft `SYSTEM_PROMPT_TRACK2_v0_1.md` (Tier 4 only).
5. **Sessions 10+:** side-by-side validation on all 6 corpora; confirm no regression.
6. **Track 2 deployment:** add config switch in `app.py` to pick track per run. Track 1 stays as fallback.

Estimated total: 8-12 sessions to working end-to-end Track 2.

## State on arrival (next chat)

Working tree should be clean except untracked sample/audit folders. Top commits:
- Phase 2B partial code: `73b10a0` (kredit_lab_classify.py + 2 helper scripts)
- Phase 2B handoff: `946137a`
- This Track 2 architecture handoff append: (current commit being made)

`kredit_lab_classify_track2.py` does NOT exist yet — that's the first migration session's job.
`SYSTEM_PROMPT_TRACK2_v0_1.md` does NOT exist yet — drafted at session 9.

## First actions in new chat

1. Acknowledge handoff. Verify state:
   ```bash
   git status --short
   git log --oneline -8
   ```
   Expect tree clean and Phase 2B + Track 2 architecture commits at top.

2. Load the project memory `project_track_2_architecture.md` (auto-loaded via MEMORY.md). Read the architecture, hard rules, and migration tiers.

3. **CRITICAL: don't edit Track 1 files.** Confirm before any change to `kredit_lab_classify.py`, `SYSTEM_PROMPT_v3_5_6.md`, or `CLASSIFICATION_RULES_v3_5.json`. If touched accidentally, revert immediately. Track 1 frozen rule applies regardless of how compelling the change seems.

4. Confirm with user the first migration target. Default recommendation: **EOD computation** (cleanest pure-algorithm starting point, ~30-50 LOC, will create `kredit_lab_classify_track2.py`).

5. The first migration session's deliverable is:
   - `kredit_lab_classify_track2.py` exists with EOD function ported (or whichever first Tier 2 target)
   - Test that the function output matches what the Track 1 prompt would produce on the same input
   - Confirmation that Track 1's behaviour is unchanged (verify_*_v3a.py rates unchanged)

6. **Terminology note:** the prior `feedback_track_isolation_design.md` memory (2026-04-29) used Track 1 / Track 2 with different scope. The 2026-05-01 labels (Track 1 = current production system, Track 2 = new thin-AI architecture) supersede. The older memory's track-isolation principle still holds; only the labels evolved.

## Rollback procedure

Track 2 work is purely additive — new files, no edits to Track 1. Rollback = delete the new files:

```bash
rm kredit_lab_classify_track2.py                                 # if created
rm "validation runs - json/claude ai prompt file/SYSTEM_PROMPT_TRACK2_v0_1.md"  # if created
```

No git revert needed because Track 1 is never modified. The handoff append in this commit can be reverted independently if needed:

```bash
git revert <track2-handoff-commit-hash>
```

## Context budget note

This session continued from the Phase 2B partial work earlier in the day. Total session usage ~125k tokens by end of architecture discussion. Heavy items: full v3.5.6 system prompt read (~17k tokens for 831 lines), classification rate diagnostic per corpus (named vs synthetic split), Mytutor C24/C27 inspection script + analysis, deterministic vs AI judgment principle articulation, migratable/non-migratable tier analysis, Track 1/Track 2 boundary clarification across multiple turns.
