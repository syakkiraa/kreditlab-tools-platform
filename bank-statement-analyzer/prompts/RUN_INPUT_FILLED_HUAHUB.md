# Filled Pre-Analysis Input — HUAHUB MARKETING SDN BHD (CIMB + Hong Leong + Maybank)

**Purpose:** First **real-workload** Track 2 trial — not a smoke. Tests
whether the v0.1 prompt handles a **multi-bank consolidation** case the
way an analyst actually works it: one company, 4 accounts across 3
banks, 6 months.

**Why this case matters:**

- All three previous Track 2 trials (Mazaa, Upell, MTC OD) were
  **single-bank** corpora. Huahub is the first multi-bank case to hit
  the v0.1 prompt.
- Memory entry: *"Principal Gas multi-bank consolidation — lower
  priority than #1/#2/#4 above."* This trial **surfaces** whether that
  deferral is still justified or whether the AI handles cross-bank
  synthesis acceptably at the narrative layer.
- The engine **does not merge across runs** — you'll get **3 separate
  Track 2 JSONs**, one per bank. The AI must do the consolidation in
  its narrative output (summing credits/debits across banks, spotting
  cross-bank own-party transfers, etc.).

**Engine outputs (attach all 3 JSONs to the same chat message):**

| # | Bank | Run config | Account(s) | Save as |
|---|---|---|---|---|
| 1 | CIMB | Pick `CIMB Bank` in app.py, upload all 12 PDFs from `Bank-Statement/CIMB/Huahub Marketing/` | **4920** + **9504** (two accounts in one run) | `track2_huahub_cimb.json` |
| 2 | Hong Leong | Pick `Hong Leong Bank`, upload all 6 PDFs from `Bank-Statement/HongLeong/Huahub Marketing/` | **28900032761** | `track2_huahub_hlb.json` |
| 3 | Maybank | Pick `Maybank`, upload all 6 PDFs from `Bank-Statement/Maybank/huahub marketing/` | **5726** | `track2_huahub_mbb.json` |

**How to use:**
1. Use the **Kredit Lab — Track 2** claude.ai project (same project +
   system prompt as the Mazaa / Principal Gas smokes). Open a **NEW
   chat** — don't reuse prior chats.
2. Open this file, edit the `(verify)` lines (Section 1 fields, RP1,
   factoring, business model, special notes), copy the
   `---BEGIN/END---` block.
3. Paste the block into the chat input.
4. **Drag all 3 Track 2 JSONs into the same message.** claude.ai
   supports multi-file attachments — they all land in the same context.
5. Send.

---

```
---BEGIN PRE-ANALYSIS INPUT---

# Pre-analysis input for THIS run

## 1. Company information

- Company name (full legal): HUAHUB MARKETING SDN BHD
- Statement period: Oct 2025 to Mar 2026 (6 months)
- Bank(s) in this run: **CIMB, Hong Leong, Maybank — 3 banks**
- Number of accounts in this run: **4 accounts total**
    - CIMB 4920
    - CIMB 9504
    - Hong Leong 28900032761
    - Maybank 5726
- Address (Hong Leong header): 43G, Jalan Ramin 2, Bandar Botanic,
  41200 Klang Selangor
- Credit context for THIS analysis: **(verify — fill in what facility
  you're considering: e.g. "RM ___K working capital line",
  "due diligence on existing OD facility renewal", etc.)**

## 2. Confirmed related parties (RP1)

** No analyst-known RPs supplied a priori. The engine's RP3 scanner
will auto-confirm any HIGH-confidence behavioural candidates per JSON;
those flow into each JSON's `report_info.related_parties` already. If
you know specific directors / family members / sister companies for
Huahub, add them here so the AI applies them across ALL 3 JSONs (the
engine only sees one JSON at a time). **

- (add any directors, family members, or sister companies you know)

(If section 2 stays empty, the AI relies on the per-JSON auto-RP only.
Cross-bank RP detection by the AI alone is a stretch — listing names
here is the way to anchor cross-bank attribution.)

## 3. Known factoring entities (for C10)

- (leave blank if none known — likely none for a marketing company,
  but verify)

## 4. Analyst decisions

### 4a. Commission cluster handling

- [x] Treat as regular expense (independent contractors / agents — DEFAULT)
- [ ] Treat as C05 salary (commission earners are on payroll as employees)

(Reasoning: Huahub appears to have proper payroll — Hong Leong Oct'25
first page shows clear "Net Pay" entries to named individuals.
Commission rule moot unless the data shows otherwise. **Verify against
top_payees in any of the 3 JSONs.**)

### 4b. Government counterparty side

- [ ] CR side from JANM / KERAJAAN: Trade revenue → C26
- [ ] CR side from JANM / KERAJAAN: Other (specify): _______
- [x] DR side: Tax / customs / statutory only (default routing)
- [x] No government counterparties expected in this run

(Marketing companies rarely deal with JANM directly. **Verify.**)

### 4c. Business model (single-select)

** VERIFY — the company name says MARKETING, but verify with the
analyst's commercial knowledge. The transaction pattern across 3
banks may reveal more (e.g. cross-bank own-party rotation suggests
trading-style cash management, not just marketing). **

- [x] Standard SME (services / trading) — default rules apply
- [ ] Tuition academy / coaching centre
- [ ] Security services
- [ ] Construction / contractor
- [ ] Agency / MLM / insurance (commission-heavy)
- [ ] Logistics / trading (factoring common)
- [ ] Marketing / digital agency / media buying
- [ ] Other: _______

### 4d. Account type override (rarely used)

- (leave blank — trust the parser. All 4 accounts likely Current /
  CR. **Verify** against each JSON's
  `accounts[].account_type_determination.locked_type`.)

## 5. Special notes for the AI

This is the **first multi-bank Track 2 run** the v0.1 prompt has
processed. You are receiving **3 separate engine JSONs** in this
chat — one per bank — covering ONE company with 4 accounts. The
engine does NOT merge them; consolidation is your job at the narrative
layer.

Items to look out for (surface in `observations.concerns[]` or
`observations.positive[]` as appropriate):

1. **Cross-bank own-party transfers.** When CIMB 4920 sends RM X to a
   counterparty and Hong Leong 28900032761 receives RM X on the same
   or next day from a counterparty named "HUAHUB MARKETING" — that's
   inter-account treasury movement, not third-party trade. The engine
   stamps own-party only within each bank's run; cross-bank own-party
   is invisible to it. **Look for matching amounts within ±2 days
   across the 3 JSONs** and surface as cross-bank own-party activity.

2. **Per-bank totals AND a consolidated view.** Each JSON has its own
   `consolidated.total_credits / total_debits`. In your `summary`
   section, give:
   - per-bank breakdown (3 rows: CIMB / HLB / MBB)
   - a combined total across all 3 banks for the period
   - clearly label the combined total as YOUR synthesis (not engine-
     derived)

3. **Salary activity.** Hong Leong Oct'25 page 1 shows named-individual
   "Net Pay" transfers (TEE BOON BENG, OIE CHONG EYAU). Cross-check
   against each JSON's `total_salary_paid` and
   `statutory_compliance.overall_status`. If salary is paid out of
   Hong Leong but EPF/SOCSO/PCB are paid out of CIMB or Maybank,
   that's normal — statutory is consolidated for the entity, not
   per-account.

4. **Account-type consistency across banks.** All 4 accounts are
   likely Current. If any one of them surfaces as OD in its JSON,
   surface that as a concern — multi-bank entities sometimes have
   one OD facility plus several CA accounts, but the analyst needs
   to know which one is the OD.

5. **Counterparty overlap across banks.** If the same counterparty
   name (e.g. a customer paying both into CIMB 4920 AND Maybank 5726)
   appears in multiple JSONs, that's a real customer of Huahub —
   surface in top_payers with combined totals across banks.

6. **Schema compliance — same rules apply per JSON.** Each JSON must
   pass v6.3.5 schema independently. Your output is ONE analysis JSON
   covering all 3 banks — do NOT produce three separate analysis
   JSONs.

7. **Do NOT re-derive engine totals.** The scope guard from Mazaa /
   Principal Gas applies per-JSON. Within each bank's slice, do NOT
   recompute `total_own_party_*`, `total_related_party_*`, etc. The
   ONLY new math you do is the **cross-bank summation** in your
   narrative summary (clearly labelled as analyst synthesis).

8. **Parser quality (Deliverable 2).** Report parser quality
   **per-bank** in Deliverable 2 — three sections (CIMB, HLB, MBB)
   with separate `overall_success_rate`, balance-check counts,
   structural notes. Don't conflate them.

---END PRE-ANALYSIS INPUT---
```

---

## Trial verification checklist (read after AI responds)

### Deliverable 1 — Analysis JSON

- [ ] `schema_version` = `"6.3.5"`.
- [ ] `report_info.company_name` = `"HUAHUB MARKETING SDN BHD"`.
- [ ] `accounts[]` count = **4** (CIMB 4920, CIMB 9504, HLB 28900032761,
      MBB 5726). NOT 3, NOT 1.
- [ ] `accounts[].bank_name` reflects all 3 banks.
- [ ] `monthly_analysis` row count = **24** (4 accounts × 6 months).
- [ ] `consolidated.total_credits / total_debits` — analyst synthesis,
      clearly labelled, sums across the 3 engine outputs.
- [ ] `flags.indicators[]` = 16 entries, `{id, name, detected, remarks}`.
- [ ] `observations.positive[] / .concerns[]` capped at 8.

### Deliverable 2 — Parser Quality Report

Expect the AI to surface:

- [ ] Per-bank parsing metrics (3 sections, not 1 combined).
- [ ] Any bank-specific structural notes (e.g. CIMB rail-prefix
      handling vs HLB description format vs MBB statement format).
- [ ] PDF integrity per bank (likely "not assessed" — pdf_integrity is
      not invoked in app.py's full_report path for the JSONs at this
      time).

### Multi-bank-specific watch items

- [ ] Did the AI **consolidate across the 3 JSONs** into one analysis,
      or did it produce three separate analyses? Must be ONE.
- [ ] Did the AI **surface cross-bank own-party transfers** (matching
      amounts within ±2 days across banks)? Or did it miss them
      entirely?
- [ ] Did the AI clearly label its **cross-bank synthesised totals**
      as analyst-derived, NOT engine-derived?
- [ ] Did the AI **hallucinate cross-bank totals** that don't match
      the sum of the per-bank engine totals?
- [ ] If counterparties overlap across banks (same name in multiple
      JSONs), did the AI **combine** their totals or report them as
      separate parties?

### Failure modes worth noting (for v0.2 spec)

If the AI does any of these, multi-bank coverage in v0.1 is
insufficient and v0.2 needs to address it:

- Produces three separate analysis JSONs instead of one.
- Misses obvious cross-bank own-party transfers visible in the data.
- Sums engine totals incorrectly (transcription error).
- Drops one of the 3 banks entirely from its analysis (missing
  attachment handling).
- Fails to attribute counterparty rows to the correct account.

---

## After the trial — what we learn

This is the first multi-bank Track 2 trial. Output answers:

| Question | What the trial tells us |
|---|---|
| Does v0.1 handle multi-bank consolidation? | Yes / partially / no |
| Is cross-bank own-party detection feasible at the AI layer? | Yes / needs engine work |
| Should multi-bank consolidation be a v0.2 prompt addition or an engine refactor? | Prompt fix / engine fix / both |
| Does claude.ai handle 3 simultaneous JSON attachments cleanly? | Yes / context-limit issues |

If v0.1 holds, multi-bank stays a deferred item with no v0.2 blocker.
If v0.1 mishandles it, v0.2 needs a dedicated multi-bank section in
the prompt, OR the engine needs a merge-across-runs helper before
this case can ship to analysts.
