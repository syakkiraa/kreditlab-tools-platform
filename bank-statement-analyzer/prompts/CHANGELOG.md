# SYSTEM_PROMPT changelog

Older changelog entries previously stacked at the top of `SYSTEM_PROMPT_v3_5_X.md` files. Moved here in v3.5.6 to slim the runtime prompt. Active rules from these versions are preserved in the current prompt file — only the historical *narration* of why-they-exist was relocated.

---

## v3.5.6 patch — 2026-04-28 (Phase 2 rule 3: amount-divergence diagnostics)

**Rule 3 (amount-divergence) shipped — light-touch diagnostics, not a threshold change.** User confirmed the existing ±RM 1.00 hard pass / fail-otherwise structure is correct ("get the grand total — that's the end of the story; sub-RM 1 drift is rounding noise, anything bigger should fail"). The bug to fix was not the threshold, it was the *visibility*: passes were silent (drift across runs invisible) and failures were too vague to act on without re-running.

**What changed in [SYSTEM_PROMPT_v3_5_6.md:692-705](validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md#L692-L705):**

1. **Always record the gap, even on PASS.** New required fields in `cleaning_stats`:
   - `cr_total_gap` = `gross_credits − Σ counterparty.total_credits` (signed, 2 dp)
   - `dr_total_gap` = `gross_debits − Σ counterparty.total_debits` (signed, 2 dp)
   - `tx_count_gap` = `total_extracted_transactions − Σ counterparty.transaction_count` (signed integer)

   On PASS the gaps are usually `0.00` but populated honestly — the analyst can now spot a parser slowly drifting RM 0.30/run before it crosses the failure line.

2. **Failure notes must be specific.** When `VALIDATION_FAILED` fires, the `observations.concerns` entry must name (a) which side(s) failed, (b) the signed gap amount(s), (c) the worst-contributing month, (d) the worst-contributing counterparty. Vague `"delta = X"` notes are no longer acceptable.

**Pass thresholds unchanged:** `|cr_total_gap| ≤ 1.00` AND `|dr_total_gap| ≤ 1.00` AND `tx_count_gap == 0` → `CLEANED`. Anything else → `VALIDATION_FAILED`. The "do NOT modify the ledger to force balance" rule stands.

**Schema impact: none.** `cleaning_stats` has no `additionalProperties: false` in `BANK_ANALYSIS_SCHEMA_v6_3_5.json` (the prompt already references undeclared fields like `rp_canonical_stamps_applied`), so the three new gap fields are schema-permissive additions. No schema bump, no Track 2 coordination required.

**Why this is the right shape:** it preserves the philosophical anchor (grand total is the truth) while killing two practical failure modes — invisible drift on PASS and unactionable notes on FAIL. Same v3.5.6 label retained; claude.ai project-knowledge swap stays a single-file replace.

**Verified live 2026-04-29 (MUHAFIZ acceptance test):** the new fields are emitted exactly as specified — `cleaning_stats.cr_total_gap = 0.0`, `dr_total_gap = -0.0` (signed, as the spec calls for), `tx_count_gap = 0`, alongside `ledger_cleaning_status: "CLEANED"`. Confirms the AI honours the rule on a clean PASS and the field shape is schema-compatible.

Phase 2 now fully shipped. Rule 3 deferral cleared.

---

## v3.5.6 patch — 2026-04-28 (Phase 2: 3 of 4 rule tightenings; rule 3 deferred)

**Three rule tightenings shipped** (rule 3 — amount-divergence — held for refinement). All cross-bank-safe.

**1. plate-as-RP-keyword exclusion (RP6).** Strings matching the Malaysian vehicle plate regex `\b[A-Z]{1,3}\d{1,4}\b` (e.g. `QPC8957`, `UQ5888`) are now explicitly excluded from RP2/RP3/RP4/RP8 auto-detection scans. These are HP reference codes already handled by the C02+C11 dual-tag rule; without the exclusion they could leak into recurring-payee detection and surface as fake "related parties".

**2. Government counterparty extension to C26 Trade Income.** Government-CR (KERAJAAN MALAYSIA / JANM / AKAUNTAN NEGARA / KASTAM / JABATAN KASTAM / PERBENDAHARAAN / KEMENTERIAN <X> / JABATAN <X> / PERBADANAN <X> / MAJLIS <X>) now routes to C26 instead of falling to Unclassified. Fixes the MUHAFIZ RM 6.4M blind spot where security-firm gov clients paid via "JANM CAWANGAN <state>" — correctly named by the parser but missed by the SDN BHD suffix test. Pre-analysis input template section 4b is the override channel: when the analyst marks "DR side: tax/customs only", this extension does not fire. Government-DR semantics unchanged (still tax / customs / statutory).

**3. IBG / DuitNow return pairing (C13 ↔ C16).** New block under C26/C27 in the prompt. When a CR row's description contains an IBG/DuitNow return prefix (`IBG-RETURN`, `RTN-IBG`, `R-IBG`, `RIBG`, `DUITNOW-RETURN`, `RDN`, `PAYMENT REJECTED`, `PYMT RETURNED`, etc.) AND a same-amount outward DR exists within ±5 business days to the same counterparty, the pair is now tagged DR=C13 (reversal), CR=C16 (inward return), exiting net flows via existing formulas. Prevents phantom outflows from polluting C27 trade expense. Pairs ≥ RM 1,000 surface in `observations.concerns`; smaller pairs are silent. Unpaired returns flag a possible cross-period or extraction gap.

**Why rule 3 was held:** the proposed tightening (delta-bucket between RM1.00 and RM50.00 surfaces in concerns but stays CLEANED, only ≥RM50 → VALIDATION_FAILED) was a guess at the direction. User opted to refine before shipping.

**Schema/rulebook unchanged.** Prompt-only patch, retains v3.5.6 label.

---

## v3.5.6 patch — 2026-04-28 (Phase 1: pre-analysis input template)

**Added `prompts/RUN_INPUT_TEMPLATE.md`.** A structured pre-supply form the analyst fills before pasting parser JSON into claude.ai. Captures: company info, confirmed RP1 list, known factoring entities, commission-cluster decision, government-counterparty side, business model, optional account-type override, free-text notes.

**Workflow change:** the filled block (delimited by `---BEGIN PRE-ANALYSIS INPUT---` / `---END PRE-ANALYSIS INPUT---`) goes ABOVE the parser JSON in the message. The AI consumes it first; the pre-analysis gate's default-assumption logic uses the analyst answers instead of falling back to defaults — eliminating the v1→v2→v3 rerun pattern caused by mid-run discovery (RP4 surfacing late, commission ambiguity, government-CR side ambiguity).

**Why this fixes the rerun loop:** the 2026-04-22 MYTUTOR efficiency review identified mid-run discovery as the dominant cause of slow runs. v3.5.6 added the gate-flags-never-blocks rule, but defaults still produced suboptimal classification when the analyst's actual answer differed (e.g. MUHAFIZ government CR worth RM 6.4M defaulted to Unclassified instead of C26 trade revenue). Pre-supply kills that loop entirely.

**v3.5.6 prompt INPUT section** updated to reference the template (item 1 in the new INPUT enumeration). When the block is present, the gate must NOT re-flag items it answers. No rule changes; input-shape doc only. Same v3.5.6 label retained — claude.ai project-knowledge swap is still a single-file replace.

**Acceptance test — PASSED 2026-04-29.** Analyst re-ran MUHAFIZ Sep 2025 – Feb 2026 CIMB corpus with the filled template ([prompts/RUN_INPUT_FILLED_MUHAFIZ.md](RUN_INPUT_FILLED_MUHAFIZ.md)) and the patched v3.5.6 prompt. All 5 expected outcomes verified in the resulting classified JSON:
- Government CR (RM 6.43M, 32.5% of gross CR) routed to C26 trade revenue — counterparties JANM, AKAUNTAN NEGARA, KERAJAAN NEGERI SARAWAK, KERAJAAN MALAYSIA, MAJLIS DAERAH KOTA T, all named in concerns with the explicit reference *"per Pre-Analysis Input directive 4b"*. Confirms the template was consumed and is authoritative.
- SHAUFIAH NUR ASHIKIN tagged as Family Member in `report_info.related_parties`. AI also surfaced the analyst's "verify relationship" hedge from section 2 — expected behaviour, not a re-flag.
- All 4 Phase 2 rules verified live (plate exclusion: no plate codes in RP list despite many `QPC8957`/`UQ5888`-style HP rows; gov-CR → C26 confirmed; rule 3 diagnostic gaps populated; IBG/DuitNow return pairing active with 4-of-9 paired and 5 unpaired surfaced in concerns with dates).
- Phase 0 BUG-001 fix verified live: the Feb 16 RM 600K `DUITNOW TO ACCOUNT EPF PAYMENT MUHAFIZ SECURITY SDN` row appears in `own_related_transactions` as `OWN`, not falsely stamped as KWSP statutory.
- Single-pass run, no v2/v3 reruns. Analyst confirmed turnaround time improved noticeably vs prior MUHAFIZ runs without the template — the workflow goal of Phase 1.

Track 1 ownership: template lives under `prompts/`, does not touch `kredit_lab_classify.py` (Track 2 territory).

---

## v3.5.6 patch — 2026-04-28

**Fixed `ledger_cleaning_status` enum mismatch.** Original v3.5.6 instructed the AI to emit `"PASSTHROUGH"` / `"PASSTHROUGH+RP_STAMPED"`, but the schema enum is `["CLEANED", "VALIDATION_FAILED", "SKIPPED"]`. Schema-validation hard gate forced the AI to silently work around the bad instruction on every run (BUG-005-DOC, surfaced in 2026-04-27 MUHAFIZ analysis run). Updated prompt to use schema-compliant values: `"CLEANED"` for normal pass-through-with-M7-stamping, `"VALIDATION_FAILED"` for totals mismatch, `"SKIPPED"` for absent/empty ledger. No other content changed.

---

## v3.5.6 — 2026-04-27

**Defensive-extraction slim-down.** Layer 1 (parser counterparty extraction across all 14 banks, completed Sprint 6 — see `prompts/NEXT_CHAT_PROMPT.md` for the Sprint 6 history) now reliably labels rows with named entities, biller names, statutory buckets, or clean UNNAMED bucket fallbacks. Re-extraction logic in this prompt was therefore dead weight that risked **two-sources-of-truth divergence** (the same bug class v3.5.4 closed for `statutory_bucket`).

**Removed (defensive re-extraction, now Layer-1 work):**
- Step 0 — Raw-Fallback Entity Extraction (in `counterparty_ledger` cleaning)
- Step 1 — Purpose text stripping
- Step 2 — Merge counterparty variants M1-M6 (kept M7 only — needs resolved RP list)
- Step 3 — Rebuild ledger after merging
- TR1-TR4 truncated-name resolution (Layer 1 owns this per bank)
- JomPAY `no_entity_name` fallback in classifier order-of-ops (parser now extracts JomPAY billers)
- Stacked v3.5.1 → v3.5.5 changelog narration (relocated here)

**Retained:**
- M7 canonical-RP-name stamping (genuinely Layer-2 work)
- Ghost-verb suppression (presentation-layer filter for top_parties; legacy corpus safety net)
- Totals validation (counterparty totals = monthly gross_credits/gross_debits)

**Net reduction:** 11.8% lines, 17.4% chars/tokens (~3,100 tokens per call).

**Schema/rulebook unchanged:** `CLASSIFICATION_RULES_v3_5.json` and `BANK_ANALYSIS_SCHEMA_v6_3_5.json` are the source of truth and not modified.

---

## v3.5.5 — 2026-04-23

Sprint 4.5 Option A. Parser's `account_type_determination.locked_type` enum reduced to `CR / OD / UNDETERMINED` only — dropped `CASH_LINE`. Islamic Cashline-i / CAP-i / SAP-i is the same revolving-credit facility as conventional Overdraft, so it locks as OD; no separate product class. Display-label enum `accounts[].account_type` collapsed back to `Current / Savings / OD`. Mapping: `locked_type == OD` → display `OD`; `locked_type == CR` → `Current` or `Savings` per header text; `locked_type == UNDETERMINED` → `Current` default. Cash Line / Cash Line-i disambiguation step in v3.5.4 removed. Schema file reference `v6_3_4` → `v6_3_5`; rulebook `v3_4` → `v3_5`.

---

## v3.5.4 — 2026-04-23

Trust-parser-metadata shift driven by 2026-04-23 review. Parser now emits authoritative fields the classifier MUST trust instead of re-computing:

1. **Trust parser counterparty statutory_bucket** — when a transaction carries `statutory_bucket == "KWSP"/"SOCSO"/"LHDN"/"HRDF"`, route C06–C09 directly from that field. Do NOT re-regex the raw description. Two sources of truth → one. Kills the FPX 20-char truncation bug (v3.5.3 missed `KUMPULAN WANG SIMPAN` because it regexed for the full phrase).
2. **Trust parser account_type_determination** — the `accounts[].account_type_determination` object contains both CR and OD trail deltas, a header signal, and a locked verdict. Use the locked verdict. Do NOT re-run the test when the parser already did.
3. **Patronymic-fragment guard** — when a transaction has `_patronymic_ambiguous_tokens: ["BA"]` (or TL/TF/FD/CT), SKIP short-form banking-acronym C10/C11/C12 rules on that row. These tokens are name fragments after `BIN/BINTI/A/L/A/P/BT/BTE`, never Banker's Acceptance / Term Loan / Trade Finance / Fixed Deposit / Current Transfer.
4. **EPF dual-band** — Malaysian combined (employer + employee) EPF remittance is 23-24% of gross salary; employer-only remittance is 11-13%. Expected band is now `11-15% OR 20-26%` (EITHER model is healthy). KDYN 22-24% is NORMAL combined, NOT anomaly.
5. **STRUCTURAL status** — sustained high EPF/SOCSO ratio (≥4 consecutive months outside both bands) is STRUCTURAL — requires analyst confirmation with entity, distinct from single-month CATCH_UP. STRUCTURAL does NOT downgrade COMPLIANT → GAPS_DETECTED by itself.
6. **Gate flags, never blocks** — removed hard-gate pausing. Pre-analysis gate runs end-to-end, producing a report with every assumption flagged in `observations.concerns[]`. Analyst decides pre- or post-evaluation.
7. **New Step 8 — schema validation hard gate** — `jsonschema.validate(analysis, BANK_ANALYSIS_SCHEMA_v6_3_5.json)` before writing output. required-field enumeration alone (Step 6) is insufficient; this catches enum / maxItems / pattern violations too.
8. **C26 Trade Income + C27 Trade Expense** — NEW categories (C17/C18 are already used for Cash Deposit/Withdrawal). Third-party-company CR (customer receipt) = C26; DR (vendor payment) = C27. Eliminates the Muhafiz "RM 11.8M unclassified CR" blind spot where real client payments from PIASAU GAS / PERTAMA FERROALLOYS / SCHENKER LOGISTICS fell to Unclassified because no rule covered ordinary trade revenue.

---

## v3.5.3 — 2026-04-21

Eight targeted fixes driven by KDYN/MUHAFIZ/MYTUTOR validation runs:

1. **Top 10 payers/payees** (was Top 5) — align with HTML renderer heading.
2. **Ghost-verb suppression rule** — `TRANSFER FR A/C`, `TRANSFER TO A/C`, `PAYMENT FR A/C`, `INTER-BANK PAYMENT INTO A/C` entries with no counterparty name attached are parser dropouts and MUST be excluded from `top_parties`.
3. **Statutory side-gate (C06–C09)** — keyword match fires ONLY when `side == "DR"` AND `not match_own_party(desc)`. Prevents `DUITNOW ... EPF PAYMENT ... <company>` CR transfers being tagged C06.
4. **EPF/SOCSO coverage intersection + cap** — `coverage_pct = len(paid_months ∩ salary_months) / len(salary_months) × 100`, always clamped `[0, 100]`. Prevents the >100% anomaly when statutory pays in a non-payroll month. Applies only to strictly-payroll-driven statutories (EPF, SOCSO).
5. **LHDN and HRDF decoupled from salary coverage** — LHDN bucket lumps PCB/MTD + CP204 + SST + stamp duty (different schedules); HRDF is exempt for small employers. Do NOT emit coverage %. Present as informational count + total amount only. Removes the 120% LHDN display on MYTUTOR and prevents similar false-correlation anomalies on future runs.
6. **Commission / `Comm` policy (C05)** — recurring `Comm` payments to individuals default to regular expense unless the user confirms agents-are-employees. Surfaced at the pre-analysis gate when `Comm` dominates individual-transfer DR volume (>20% of gross debits).
7. **`effective_match_rate`** replaces `pattern_match_rate` as the canonical parser-quality grade driver. `special_bucket` entries (AUTOPAY CHARGES, OTHER TRANSFER FEE, CASH CHQ DR, HSE CHQ DEPOSIT) are correct handling, not failure.
8. **Schema-fields cheatsheet** — pre-flight step added: dump every output section's `required[]` array from the schema BEFORE writing the output, use exact field names verbatim.

---

## v3.5.2 — 2026-04-19

Adds mandatory PRE-ANALYSIS GATE section. Account type detection and dual-formula balance trail verification must run BEFORE any classification or diagnostic conclusions. Prevents misdiagnosis of OD accounts as "swapped columns" or parser bugs. All other content unchanged from v3.5.1.

---

## v3.5.1 — 2026-04-18

Adds OD (overdraft / DR-balance) account handling throughout BALANCE TRAIL RECONCILIATION and PARSER QUALITY AUDIT (sections A and D). OD accounts use the inverted trail rule (`opening + debits − credits = closing`) because balance is stored as positive debt magnitude. Ambank OD is an exception (pre-negated — uses CR rule). Prior versions incorrectly graded OD accounts as "F" with "inverted columns" even when parser output was correct.
