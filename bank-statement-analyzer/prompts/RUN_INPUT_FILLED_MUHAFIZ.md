# Filled Pre-Analysis Input — MUHAFIZ acceptance test

**Purpose:** the filled template for the MUHAFIZ Sep 2025 – Feb 2026 CIMB run, used as the Phase 1 + Phase 2 acceptance test for v3.5.6.

**How to use:**
1. Open this file.
2. Copy everything between the two `---BEGIN PRE-ANALYSIS INPUT---` / `---END PRE-ANALYSIS INPUT---` markers below.
3. In claude.ai web (Kredit Lab project), start a new chat and paste the copied block into the message input.
4. Below the pasted block, attach the fresh `Full Report CIMB Muhafiz.json` (re-run the parser first; the existing one in `validation runs - json/claude ai prompt file/Full Report Sample/` predates Sprint 7 parser fixes that affect MUHAFIZ specifically).
5. Send.

**Before sending — verify:**
- Section 2 RP1 list: confirm SHAUFIAH NUR ASHIKIN's relationship to MUHAFIZ; add any other directors / family / sister companies you know.
- Section 4b: confirmed gov-CR is trade revenue (~RM 6.4M from JANM CAWANGAN entries) per the MUHAFIZ Sep25-Feb26 challenges report.

---

```
---BEGIN PRE-ANALYSIS INPUT---

# Pre-analysis input for THIS run

## 1. Company information
- Company name (full legal): MUHAFIZ SECURITY SDN BHD
- Statement period: Sep 2025 to Feb 2026
- Bank(s) in this run: CIMB
- Number of accounts in this run: 1

## 2. Confirmed related parties (RP1)

- SHAHARUDDIN BIN SAMSI (Director)
- SHAUFIAH NUR ASHIKIN (verify relationship before sending — likely family/director-related)
- (add any other directors, family members, or sister companies you know)

## 3. Known factoring entities (for C10)

(none expected for security-services business; leave blank if no factoring relationship)

## 4. Analyst decisions

### 4a. Commission cluster handling
- [x] Treat as regular expense (independent contractors / agents — DEFAULT)
- [ ] Treat as C05 salary (commission earners are on payroll as employees)

### 4b. Government counterparty side
- [x] CR side from JANM / KERAJAAN: Trade revenue (operating income from gov clients) → C26
- [ ] CR side from JANM / KERAJAAN: Other (specify in section 5): _______
- [x] DR side: Tax / customs / statutory only (default routing)
- [ ] No government counterparties expected in this run

### 4c. Business model (single-select)
- [ ] Standard SME (services / trading) — default rules apply
- [ ] Tuition academy / coaching centre (commission-heavy, fee-CR-dominant)
- [x] Security services (government clients common, guard salary patterns)
- [ ] Construction / contractor (progress payments, retention sums)
- [ ] Agency / MLM / insurance (commission-heavy, multi-tier payouts)
- [ ] Logistics / trading (factoring common)
- [ ] Other: _______

### 4d. Account type override (rarely used)

- (leave blank — trust the parser)

## 5. Special notes for the AI

This run is the Phase 1 + Phase 2 acceptance test for v3.5.6 (post-Sprint-7 parser).
Expected outcomes to verify in the output:
- Government CR (~RM 6.4M from JANM CAWANGAN entries) routed to C26 trade revenue
- SHAUFIAH NUR ASHIKIN tagged as RP4 in observations.related_parties (do not re-flag in concerns)
- counterparty_ledger.cleaning_stats must include populated cr_total_gap, dr_total_gap, tx_count_gap
  (signed numbers — usually 0.00 / 0.00 / 0 on a clean run; populate honestly even on PASS)
- ledger_cleaning_status must be one of CLEANED / VALIDATION_FAILED / SKIPPED (schema enum)
- No Phase 2 regressions: no Malaysian vehicle plate codes (e.g. QPC8957) appearing as RP candidates;
  IBG/DuitNow returns paired (DR=C13, CR=C16) if any exist in the data

---END PRE-ANALYSIS INPUT---
```
