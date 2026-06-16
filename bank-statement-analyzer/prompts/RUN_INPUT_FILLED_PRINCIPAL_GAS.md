# Filled Pre-Analysis Input — PRINCIPAL GAS SDN BHD (Bank Islam)

**Purpose:** Track 2 v0.1 Tier 4 prompt smoke — first real-world end-to-end run
of `SYSTEM_PROMPT_TRACK2_v0_1.md` against engine output. Highest-signal
corpus because Track 2 demonstrably corrects four Track 1 bugs here (s21
side-by-side; see [TRACK_2_HANDOFF_AFTER_SESSION_21.md](TRACK_2_HANDOFF_AFTER_SESSION_21.md)
§"Principal Gas — Track 2 corrects 4 Track 1 bugs").

**Engine output (paste with this template):**
`/tmp/track2_s21/principal_gas/track2.json` — 130 KB, 176 txns, 5 months,
Aug-Dec 2025, Bank Islam single account.

**How to use:**
1. Open this file.
2. Open a fresh chat in claude.ai (Kredit Lab project) with
   `SYSTEM_PROMPT_TRACK2_v0_1.md` set as the project's system prompt.
3. Copy everything between the two `---BEGIN PRE-ANALYSIS INPUT---` /
   `---END PRE-ANALYSIS INPUT---` markers below.
4. Paste it into the message input.
5. Below the pasted block, attach `/tmp/track2_s21/principal_gas/track2.json`.
6. Send.

**Before sending — verify EVERY entry marked (verify):**
The RP1 list and business-model guess below are based on engine-output
pattern analysis only. I have no independent confirmation that ROSDZAMAN
BIN MOHD or any other individual is a director / family member. Remove
any (verify) line you can't confirm — letting an unknown name through as
confirmed RP1 is worse than leaving the engine's HIGH-confidence empty
set as-is.

---

```
---BEGIN PRE-ANALYSIS INPUT---

# Pre-analysis input for THIS run

## 1. Company information
- Company name (full legal): PRINCIPAL GAS SDN BHD
- Statement period: Aug 2025 to Dec 2025
- Bank(s) in this run: Bank Islam
- Number of accounts in this run: 1

## 2. Confirmed related parties (RP1)

** VERIFY each entry before sending — these are engine-pattern suggestions
only, not analyst-confirmed. Remove any name you don't recognise. **

- (verify) ROSDZAMAN BIN MOHD Y — appears as a single ~RM 10K DR under
  the rail-prefix-stripped CDB CS shape. Could be a director / staff loan
  / one-off vendor. If you don't know this name, REMOVE this line.
- (add any other directors, family members, or sister companies you know —
  e.g. PRINCIPAL GAS holding company, related gas-trading sister entities)

(If section 2 stays empty after your verification pass, that is fine —
the engine's HIGH-confidence RP3 scanner returned zero auto-confirmed
parties on this corpus.)

## 3. Known factoring entities (for C10)

- (leave blank if none known — engine's `known_factoring_entities` is
  also empty for this run)

## 4. Analyst decisions

### 4a. Commission cluster handling
- [x] Treat as regular expense (independent contractors / agents — DEFAULT)
- [ ] Treat as C05 salary (commission earners are on payroll as employees)

(Reasoning: no obvious commission-shaped DRs in the engine's top_payees
or unclassified — sticking with the default.)

### 4b. Government counterparty side
- [ ] CR side from JANM / KERAJAAN: Trade revenue (operating income from gov clients) → C26
- [ ] CR side from JANM / KERAJAAN: Other (specify in section 5): _______
- [x] DR side: Tax / customs / statutory only (default routing)
- [x] No government counterparties expected in this run

(Reasoning: no JANM / KERAJAAN / KASTAM / LHDN counterparties visible in
top_payers, top_payees, or unclassified rows. Statutory CR side is
unlikely for an industrial-gas distributor.)

### 4c. Business model (single-select)

** VERIFY — "PRINCIPAL GAS" suggests industrial-gas distribution /
trading. Confirm or correct based on what you know. **

- [ ] Standard SME (services / trading) — default rules apply
- [ ] Tuition academy / coaching centre (commission-heavy, fee-CR-dominant)
- [ ] Security services (government clients common, guard salary patterns)
- [ ] Construction / contractor (progress payments, retention sums)
- [ ] Agency / MLM / insurance (commission-heavy, multi-tier payouts)
- [x] Logistics / trading (factoring common)
- [ ] Other: _______

(Reasoning: engine's unclassified DRs include "Manpower Supply" and
"Ball Valve" memo lines — consistent with industrial-gas /
ball-valve-and-fittings distribution. Trading vertical fits.)

### 4d. Account type override (rarely used)

- (leave blank — trust the parser. Engine's
  `account_type_determination.locked_type` is "CR" with LOW confidence
  per Track 2 default; if you've inspected the BIMB statement PDF and
  confirmed this is NOT an OD/Cash Line-i account, that confirms the
  default.)

## 5. Special notes for the AI

This is the **first real-world Track 2 Tier 4 smoke** — v0.1 prompt
against the s21 engine output. The engine has already done Tier 1-3
deterministically (account-type, balance reconciliation, own/related,
salary / statutory / loan / cheque / cash / trade classification,
flags scaffold, observations baseline). Your job is Tier 4 only per
§3 of the system prompt.

Specific items to look out for (not to fix — to surface in
`observations.concerns[]` if found):

1. **`flags.indicators[]` schema conformance.** The engine emits each
   indicator with `{id, name, verdict: None}`, but
   `BANK_ANALYSIS_SCHEMA_v6_3_5.json` requires `{id, name, detected:
   bool, remarks: str}` (see `$defs` — `verdict` is not in the schema).
   Per system prompt §8, validate before emitting Deliverable 1. If
   validation fails on this field, that is an ENGINE bug — surface it
   in Deliverable 2 (Parser Quality Report) as a Track 2 engine
   revisit candidate, then fill `detected` + `remarks` from the
   consolidated numbers (round-figure CR, statutory_compliance status,
   etc.) so Deliverable 1 validates.

2. **Unclassified large DRs — counterparty-extraction gap.** 19 rows
   totalling RM 357K fall through all dispatcher rungs. Their
   descriptions follow the shape `"9124 CDB CS TO IBFTS3 <NAME>
   <memo>"` (Bank Islam rail prefix `CDB CS` not stripped by the
   parser). Per system prompt §3.7, do NOT reclassify in v0.1 —
   surface as "N unclassified large DR rows look like trade expense —
   BIMB rail-prefix stripping gap, parser revisit candidate" and
   include the RM 357K total + the dominant counterparties (FLUX
   SOURCE SDN BHD, OPTIMUS DISTRIBUTOR, NYLAFLEX, PISER FUEL, etc.).

3. **Salary detection — single-month surface.** Engine detects only
   2025-10 as a salary month (`total_salary_paid = RM 44,770.30` via
   the v3.5 wider C05 regex catching "Net Pay"). Statutory compliance
   verdict is CRITICAL because EPF / SOCSO each show only 1 paid
   month (2025-11) against 1 salary month. This is the v3.5 LOCKED
   behavior — confirm in observations but do not override.

4. **No PDF integrity alerts.** `pdf_integrity` is empty `{}`. The
   engine did not run the integrity layer for this corpus (parser-side
   only). Don't fabricate alerts; the Deliverable 2 section can note
   "PDF integrity not assessed in this run."

5. **Parser quality.** `parsing_metadata.overall_success_rate = 1.0`
   on 176 txns across 5 months, all 5 balance checks passed. Strong
   parser coverage. The only quality gap is the rail-prefix-stripping
   issue above (counterparty extraction, not amount extraction).

---END PRE-ANALYSIS INPUT---
```

---

## Smoke verification checklist (read this after AI responds)

The AI should emit **two deliverables** per system prompt §5.

### Deliverable 1 — Analysis JSON

Confirm these in the AI's output JSON:

- [ ] `schema_version` unchanged: `"6.3.5"`.
- [ ] `report_info.company_name` = `"PRINCIPAL GAS SDN BHD"` (per
      §4 step 1 — copied literally from Pre-Analysis Input section 1).
- [ ] `flags.indicators[]` — 16 entries, each with `{id, name, detected,
      remarks}` (NOT `verdict`). Numbers come from consolidated. Flag 11
      `Related Party Transactions` should be `detected=false` since
      `related_party_cr / dr` are zero unless section 2 named someone.
- [ ] `observations.positive[]` and `observations.concerns[]` — strings
      only, no nested objects. Cap 8 per list.
- [ ] `consolidated.statutory_compliance.overall_status` = `"CRITICAL"`
      preserved (engine verdict; do NOT delete per §6).
- [ ] `monthly_analysis` row count = 5 (one per month).
- [ ] `accounts` count = 1.
- [ ] `top_parties.top_payers` / `top_payees` — `{rank, party_name,
      total_amount, transaction_count, is_related_party,
      monthly_breakdown}`. Note system-prompt §8 says `total_rm` but
      the actual schema field is `total_amount`. AI may follow the
      prompt and emit `total_rm` (wrong vs schema) or the engine input
      `total_amount` (correct vs schema). Either way: **note which it
      did** — that's a prompt-vs-schema reconciliation item for v0.2.
- [ ] No new top-level keys invented; 15 existing keys preserved.

### Deliverable 2 — Parser Quality Report

Confirm the AI surfaces:

- [ ] Total txns extracted: 176 across 5 months (Aug-Dec 2025).
- [ ] Per-bank extraction coverage: 100% (`overall_success_rate = 1.0`).
- [ ] PDF integrity alerts: none / not assessed.
- [ ] Parser revisit candidate: BIMB `CDB CS` rail-prefix stripping —
      19 unclassified large DRs (RM 357K) where the counterparty is
      visible in the description but extraction left the rail prefix.

### Tier 4 ergonomics (judgment calls — note the AI's behavior)

- [ ] Did the AI re-run classification from scratch? It MUST NOT.
- [ ] Did the AI promote any MEDIUM-confidence RP candidates? It MUST NOT
      (v0.1 scope guard §7).
- [ ] Did the AI re-derive `monthly_analysis` totals? It MUST NOT (§6).
- [ ] Did the AI follow the trust order (Pre-Analysis Input > Engine >
      Rulebook > inference) when filling flag remarks?
- [ ] Did the AI cap observations at 8 each and drop the lowest-signal
      items first?
- [ ] How clean is the narrative voice? Tier 4 polish is half the value.

### Failure modes worth noting (for v0.2 spec)

If the AI does any of these, the prompt needs tightening in v0.2:

- Hallucinates counterparty extraction (invents a clean party name not
  in the engine output).
- Promotes ROSDZAMAN or another MEDIUM-confidence row to confirmed RP
  without section 2 confirmation.
- Re-computes `total_salary_paid` based on its own regex pass over
  the unclassified rows.
- Adds a `verdict` field to `flags.indicators` instead of `detected` +
  `remarks` (would indicate prompt §3.1 needs to spell out the field
  names explicitly).
- Touches `classification_config.rulebook_version` or
  `execution_mode`.

---

## After the smoke

Record findings in:

- `prompts/CHANGELOG.md` under a Track 2 v0.1 entry (or wherever the
  Track 2 changelog lives if not yet started).
- If the engine emits `verdict` instead of `detected/remarks` and the
  AI can't fix it cleanly, that is a Track 2 engine-side bug — open a
  Track 2 session to fix the indicator emit in
  `kredit_lab_classify_track2.py` before the next analyst trial.
- If §8 of `SYSTEM_PROMPT_TRACK2_v0_1.md` (the `total_rm` typo) tripped
  validation, fix to `total_amount` in v0.2 of the system prompt.
