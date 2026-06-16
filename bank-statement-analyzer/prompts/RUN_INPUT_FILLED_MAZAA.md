# Filled Pre-Analysis Input — 010 MAZAA SDN BHD (Public Bank)

**Purpose:** Track 2 v0.1 Tier 4 prompt smoke #2 — second corpus, different
bank, deliberately structurally harder than the Principal Gas smoke (#1).
Confirms the v0.1 prompt generalises beyond Bank Islam.

**Why Mazaa is a tougher smoke than Principal Gas:**

- Principal Gas had corporate counterparty names visible behind the BIMB
  `CDB CS` rail prefix (FLUX SOURCE SDN BHD, MERCHANT STREET, etc.) — the
  AI had material to reason about.
- Mazaa has **almost no counterparty names in descriptions.** 497
  transactions, but >90% are Public Bank rail-only strings: `TRSF CR`,
  `TRSF DR`, `RMT CR`, `DEP-ECP`, `DUITNOW TRSF CR`. The AI must do Tier
  4 with a much thinner counterparty surface.
- Engine output is **338 KB** — manageable for claude.ai.

**Engine output (paste with this template):**
[validation runs - json/Track 2 engine outputs/Track 2 Engine Output - Mazaa (s21).json](../validation%20runs%20-%20json/Track%202%20engine%20outputs/Track%202%20Engine%20Output%20-%20Mazaa%20(s21).json)
— 347 KB, 497 txns, 6 months (Jan-Jun 2025), Public Bank single account
3814592414.

**How to use:**
1. Use the SAME claude.ai project + system prompt as the Principal Gas
   smoke (Kredit Lab — Track 2). Open a NEW chat in that project (don't
   reuse the Principal Gas chat — fresh context per run).
2. Open this file, edit the `(verify)` lines, copy the
   `---BEGIN/END---` block.
3. Paste the block into the chat input.
4. Drag-and-drop the engine output JSON into the same message.
5. Send.

---

```
---BEGIN PRE-ANALYSIS INPUT---

# Pre-analysis input for THIS run

## 1. Company information
- Company name (full legal): 010 MAZAA SDN BHD
- Statement period: Jan 2025 to Jun 2025
- Bank(s) in this run: Public Bank
- Number of accounts in this run: 1

## 2. Confirmed related parties (RP1)

** No analyst-known RPs supplied — engine's HIGH-confidence RP3 scanner
returned zero auto-confirmed parties on this corpus. Leave blank unless
you know specific directors / family members / sister companies for
Mazaa. **

- (add any directors, family members, or sister companies you know)

(If section 2 stays empty after your verification pass, that is fine —
the engine has flagged some patterns internally without surfacing them.)

## 3. Known factoring entities (for C10)

- (leave blank if none known)

## 4. Analyst decisions

### 4a. Commission cluster handling
- [x] Treat as regular expense (independent contractors / agents — DEFAULT)
- [ ] Treat as C05 salary (commission earners are on payroll as employees)

(Reasoning: no salary detected in engine output — `total_salary_paid =
0.0`. Commission cluster is moot; sticking with default.)

### 4b. Government counterparty side
- [ ] CR side from JANM / KERAJAAN: Trade revenue (operating income from gov clients) → C26
- [ ] CR side from JANM / KERAJAAN: Other (specify in section 5): _______
- [x] DR side: Tax / customs / statutory only (default routing)
- [x] No government counterparties expected in this run

(Reasoning: no JANM / KERAJAAN / KASTAM / LHDN counterparties visible in
top_payers, top_payees, or unclassified rows.)

### 4c. Business model (single-select)

** VERIFY — "010 MAZAA SDN BHD" name doesn't reveal the vertical. The
data pattern (55 small TRSF CR txns averaging RM 1,780, two large June
`RMT CR AT CPC MAZAA` credits totalling RM 845K, no salary or statutory
payments, no government counterparties, no cheque traffic) is consistent
with several possibilities — pick what you actually know. **

- [x] Standard SME (services / trading) — default rules apply
- [ ] Tuition academy / coaching centre (commission-heavy, fee-CR-dominant)
- [ ] Security services (government clients common, guard salary patterns)
- [ ] Construction / contractor (progress payments, retention sums)
- [ ] Agency / MLM / insurance (commission-heavy, multi-tier payouts)
- [ ] Logistics / trading (factoring common)
- [ ] Other: _______

(Defaulted to Standard SME — change if you know more.)

### 4d. Account type override (rarely used)

- (leave blank — trust the parser. Engine's
  `account_type_determination.locked_type` is "CR" with LOW confidence;
  account number `3814592414` is a Public Bank Current account.)

## 5. Special notes for the AI

This is the **second Track 2 Tier 4 smoke** — same v0.1 prompt, different
bank and structurally different corpus, to confirm the prompt generalises
beyond Bank Islam.

Items to look out for (not to fix — to surface in
`observations.concerns[]` if found):

1. **Counterparty-extraction is severely limited on Public Bank.** Of
   497 transactions, only 5 unclassified rows have any company name in
   the description (the `RMT CR AT CPC MAZAA SDN. BHD.` and `DUITNOW TRSF
   CR ... MAZAA SDN BHD` rows). The remaining ~492 transactions are
   pure Public Bank rail labels: `TRSF CR/DR` (84 rows), `DEP-ECP` (many
   rows), `DR-ECP` (many rows), `TSFR FUND CR-ATM/EFT 603451` (1 row).
   This is structural to Public Bank's PDF format — NOT a parser bug
   the AI should reclassify around. Surface as "Public Bank statement
   format does not include third-party counterparty names in
   transaction descriptions — counterparty-level analysis limited to
   own-account references."

2. **Engine own-party detection gap (real Track 2 engine bug
   candidate).** `total_own_party_cr = 0` and `total_own_party_dr = 0`
   despite three CR rows containing the literal string `MAZAA SDN BHD`
   (RM 12K + RM 45K + RM 800K + RM 10K — the latter two appearing
   together for ~RM 855K of obvious own-party activity). The engine
   should have stamped these as OWN-party via the company-name match
   rung. Note this in `observations.concerns[]` as a Track 2 engine
   revisit candidate, but do NOT reclassify in v0.1.

3. **All credits are unclassified.** `total_unclassified_cr =
   1,137,592.94 = gross_credits` — the engine has no classification
   path for any of Mazaa's credit transactions (the rail-only
   descriptions defeat every rung). Surface as a Tier-4 awareness item.
   Numeric totals (gross_credits, net_credits, monthly net trend) are
   still authoritative; only the bucket attribution is missing.

4. **Statutory verdict COMPLIANT despite zero contributions.** Engine
   emitted `statutory_compliance.overall_status = "COMPLIANT"` because
   `salary_months_active = 0` — v3.5 logic treats "no salary detected"
   as "no employer obligation". This is correct LOCKED behavior. Do NOT
   over-react in `observations.concerns[]`; this is by-design for
   non-employer entities.

5. **Round-figure CR RM 810,000 is the deliberate v3.5 divergence.**
   The s21 handoff documents this — Track 2 uses `amount % 10000 == 0`
   per v3.5 LOCKED, while the older v3.x rule was `% 1000`. The
   RM 810K matches the v3.5 spec. Surface as a Round Figure CR flag
   firing legitimately; do NOT call it a bug.

6. **One big June RM 800K "RMT CR AT CPC MAZAA" credit.** This is the
   driver of the High Value CR flag — single largest CR in the period.
   Combined with the RM 45K sibling on the same day, ~RM 845K flowed in
   from a Mazaa-named source. Most likely an inter-account transfer
   (CPC = some Mazaa-controlled facility), but engine couldn't
   confirm. Flag as "single-day inflow RM 845K from Mazaa-named source
   — likely inter-account; verify against companion accounts if
   available."

7. **No PDF integrity, no FX, no cheque, no cash — payment activity
   concentrated on Public Bank electronic rails.** `pdf_integrity = {}`
   (parser-side integrity layer not invoked); `total_fx_credits/debits
   = 0`; `total_cheque_* = 0`; `total_cash_* = 0`. Low channel-blind
   risk; high electronic-rail concentration.

8. **Parser quality.** `parsing_metadata.overall_success_rate = 1.0`,
   6/6 balance checks passed, data completeness COMPLETE. Strong
   parser coverage on amounts and balances; counterparty extraction is
   the only structural gap.

---END PRE-ANALYSIS INPUT---
```

---

## Smoke verification checklist (read after AI responds)

### Deliverable 1 — Analysis JSON

Compared to Principal Gas's checklist, three Mazaa-specific items:

- [ ] `schema_version` unchanged: `"6.3.5"`.
- [ ] `report_info.company_name` = `"010 MAZAA SDN BHD"`.
- [ ] `flags.indicators[]` — 16 entries, `{id, name, detected, remarks}`
      shape (NOT `verdict`).
- [ ] Flag #10 `Own Party Transactions` — should be `detected=false`
      since engine emitted `total_own_party_cr/dr = 0`. The AI should
      NOT silently fix the engine bug; instead flag in
      `observations.concerns[]` that the engine missed Mazaa-named CRs.
- [ ] Flag #3 `Round Figure Credits (AML)` — `detected=true`, RM 810,000.
      AI should NOT call this a bug (v3.5 spec).
- [ ] Flag #4 `High Value Credits (>3x EOD)` — `detected=true`. **Watch
      whether the AI conflates this with #9 again** (same minor error
      as Principal Gas).
- [ ] `observations.positive[] / .concerns[]` capped at 8.
- [ ] `consolidated.statutory_compliance.overall_status = "COMPLIANT"`
      preserved (do NOT flip to CRITICAL — engine verdict stands).
- [ ] `monthly_analysis` row count = 6 (one per month, Jan-Jun 2025).
- [ ] `accounts` count = 1.
- [ ] `top_parties.top_payers/payees` use `total_amount` not `total_rm`.

### Deliverable 2 — Parser Quality Report

Expect the AI to surface:

- [ ] 497 transactions across 6 months on 1 Public Bank account.
- [ ] Overall success rate 100% (6/6 balance checks).
- [ ] **Public Bank rail-only descriptions** as the structural limitation
      (vs Principal Gas where it was BIMB `CDB CS` rail-prefix stripping).
- [ ] Account number extraction: **3814592414 present** (vs Principal
      Gas where `_unknown` was the bug). Good — confirms PBB parser
      extracts the account number; BIMB doesn't.
- [ ] PDF integrity: not assessed.

### Tier 4 ergonomics — Mazaa-specific watch items

- [ ] Did the AI try to reclassify any of the 5 `MAZAA SDN BHD`-named
      unclassified rows into own-party? It MUST NOT (v0.1 scope guard).
- [ ] Did the AI call the COMPLIANT status a bug? It MUST NOT (v3.5
      LOCKED — no salary = no obligation).
- [ ] Did the AI call the round-figure CR a bug? It MUST NOT (v3.5
      LOCKED rule).
- [ ] Did the AI hallucinate counterparty names that aren't in the
      engine output? Watch for this — Mazaa has very few names, so any
      invented name is a confabulation. (Principal Gas had real names
      to anchor against; Mazaa doesn't.)

### Failure modes worth noting (for v0.2 spec)

If the AI does any of these on Mazaa, the prompt drift threshold has
been crossed and v0.2 needs to tighten:

- Promotes the `RMT CR AT CPC MAZAA SDN. BHD.` row to confirmed own-party
  (instead of flagging the engine gap).
- Re-computes `total_own_party_cr/dr` based on its own description-
  matching pass.
- Marks COMPLIANT as a false positive on a no-salary entity.
- Hallucinates third-party counterparty names absent from the engine
  output.

---

## After the smoke — what we learn

Combining Mazaa with Principal Gas, the smoke matrix gives us:

| Dimension | Principal Gas | Mazaa |
|---|---|---|
| Bank | Bank Islam | Public Bank |
| Vertical (analyst input) | Logistics/trading | Standard SME |
| Counterparty visibility | Partial (corp names behind rail prefix) | Minimal (rail only) |
| Salary activity | Yes (1 month) | None |
| Statutory verdict | CRITICAL | COMPLIANT |
| Own-party detection | Working (engine stamped 2.34M CR) | Broken (0 CR / 0 DR) |
| Tier 4 surface | Rich | Thin |

If v0.1 prompt holds on Mazaa with no scope drift, we have strong
evidence it ships for first analyst trial. v0.2 fixes (the 3 from
Principal Gas + anything new) can land as a single small commit.
