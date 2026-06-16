# Pre-Analysis Input Template — claude.ai web workflow

**What this is:** the structured pre-supply form the analyst fills before pasting parser JSON into claude.ai. Eliminates the v1 → v2 → v3 rerun pattern caused by mid-run discovery (RP4 surfacing late, commission ambiguity, government-counterparty side ambiguity, etc.). The AI consumes this template first → has all decisions upfront → no mid-run re-classification.

**How to use:**

1. Copy everything between the `---BEGIN PRE-ANALYSIS INPUT---` and `---END PRE-ANALYSIS INPUT---` markers below into a fresh chat in claude.ai (Kredit Lab project).
2. Fill in every section. Leave a field blank only if it genuinely doesn't apply — do NOT delete the heading; the AI uses presence/absence as a signal.
3. Below the filled template, paste / attach the parser `full_report.json`.
4. Send. The AI will (a) load `SYSTEM_PROMPT_v3_5_6.md` from project knowledge, (b) consume this template, (c) classify the parser data without pausing for analyst confirmation.

**Why every section matters:** see the per-section notes. They map 1:1 to the v3.5.6 PRE-ANALYSIS GATE default-assumption flags (commission cluster, RP4 candidates, account-type confidence) — pre-supplying answers here means the gate doesn't need to flag-and-default.

---

```
---BEGIN PRE-ANALYSIS INPUT---

# Pre-analysis input for THIS run

## 1. Company information
- Company name (full legal): _______
- Statement period: _______ to _______
- Bank(s) in this run: _______
- Number of accounts in this run: _______

## 2. Confirmed related parties (RP1)

List every director, family member, sister company, subsidiary, holding company,
or otherwise-confirmed related party the analyst already knows. The AI uses these
as confirmed RP1 — no MEDIUM-confidence guessing, no auto-RP detection needed
on these names.

Format: NAME (relationship)

- _______
- _______
- _______

(Add more lines as needed. Leave blank only if there are genuinely none.)

## 3. Known factoring entities (for C10)

List third-party factoring / invoice-financing companies that have a confirmed
factoring relationship with this entity. Used to route C10 (Factoring Receipt /
Repayment) without re-deriving from description text.

- _______
- _______

(e.g. PLANWORTH GLOBAL, GROWTHBOND CAPITAL. Leave blank if none.)

## 4. Analyst decisions

### 4a. Commission cluster handling

Commission-shaped DR transactions ("COMM", "COMMISSION", "KOMISEN", etc.) to
individuals can be either C05 salary or regular operating expense. The default
when this field is blank = regular expense. Confirm explicitly:

- [ ] Treat as regular expense (independent contractors / agents — DEFAULT)
- [ ] Treat as C05 salary (commission earners are on payroll as employees)

### 4b. Government counterparty side

Transactions to/from JANM, KERAJAAN MALAYSIA, AKAUNTAN NEGARA, KASTAM, LHDN,
KWSP, PERKESO, etc. can be either trade revenue (CR) or tax / statutory (DR).
The AI normally infers from side, but confirm explicitly when the entity has
recurring government counterparties:

- [ ] CR side from JANM / KERAJAAN: Trade revenue (operating income from gov clients) → C26
- [ ] CR side from JANM / KERAJAAN: Other (specify in section 5): _______
- [ ] DR side: Tax / customs / statutory only (default routing)
- [ ] No government counterparties expected in this run

### 4c. Business model (single-select)

Different business models change the prior on certain rules. Pick the closest:

- [ ] Standard SME (services / trading) — default rules apply
- [ ] Tuition academy / coaching centre (commission-heavy, fee-CR-dominant)
- [ ] Security services (government clients common, guard salary patterns)
- [ ] Construction / contractor (progress payments, retention sums)
- [ ] Agency / MLM / insurance (commission-heavy, multi-tier payouts)
- [ ] Logistics / trading (factoring common)
- [ ] Other: _______

### 4d. Account type override (rarely used)

Only fill if the parser's `account_type_determination.locked_type` is wrong AND
you have inspected the PDF header text yourself. Empty = trust parser.

- Account number(s) and corrected type: _______

## 5. Special notes for the AI

Free text. Anything else the analyst wants the AI to know about this run.
Examples: known parser quirks, expected anomalies (one-off large transfer,
director loan repayment), known data gaps, prior-run findings to carry forward.

_______

---END PRE-ANALYSIS INPUT---
```

---

## Acceptance test

Per `prompts/TRACK_1_HANDOFF.md` Phase 1 acceptance:

On the MUHAFIZ corpus:
- **Without template (baseline):** previous run had unclassified RM 6.4M government revenue + missed SHAUFIAH NUR ASHIKIN as RP4. Required 2-3 rerun passes.
- **With template:** pre-supply MUHAFIZ's RPs (including SHAUFIAH NUR ASHIKIN) in section 2, pre-supply "government CR = trade revenue" in section 4b, pre-supply "Security services" in section 4c. Both issues should resolve in a single run, no v2.

Run this end-to-end once and record the result in `prompts/CHANGELOG.md` under a Phase 1 entry.

---

## Field-design rationale

| Section | Maps to v3.5.6 prompt | Why pre-supplying matters |
|---|---|---|
| 1. Company info | INPUT items 1-2 | Already pasted today; standardising the format prevents typos in `report_info.company_name`. |
| 2. Confirmed RP1 | INPUT item 3 + Step 7 RP4 default | Kills the auto-RP-detect mid-run loop; analyst-known RPs are HIGH confidence directly. |
| 3. Factoring entities | INPUT item 4 | Direct C10 routing without re-derivation. |
| 4a. Commission | Step 5 trigger + Step 7 commission default | Removes the >20% commission-cluster pause. AI defaults to regular expense; analyst can flip to C05 explicitly. |
| 4b. Gov counterparty | Step 7 government-revenue default (added via Phase 2 in handoff) | Prevents government CR being parked in Unclassified; the MUHAFIZ RM 6.4M issue. |
| 4c. Business model | Cross-cutting prior | Tuition academies need different commission priors than security firms; pre-supplying the business shape lets the rule engine pick the right defaults. |
| 4d. Account-type override | Step 2-4 override channel | Used <5% of runs; explicit override path so analyst doesn't have to argue with the parser verdict mid-run. |
| 5. Special notes | Free text | Catch-all. Anything that doesn't fit a structured field. |

---

## Maintenance notes

- This template lives under Track 1 ownership (`prompts/` namespace). Track 2 (`kredit_lab_classify.py`) does not consume it directly today; Phase 7 will decide whether the Python classifier reads the same template format.
- When `SYSTEM_PROMPT_v3_5_X.md` bumps version, re-check that section field names still match the INPUT section of the new prompt.
- When `CLASSIFICATION_RULES_v3_X.json` adds a new analyst-decision flag (e.g. a new pre-analysis trigger), add a corresponding section here. Keep one section per decision; do not bundle.
