# /loop — Improve classification keywords

**Goal:** raise the deterministic classification rate by discovering transaction patterns that the parser currently misses, and adding them to BOTH the parser and the AI classification rules.

## Architecture — two layers, same keywords

```
PDF → Parser (app.py) → full_report.json → Claude AI (reads rules) → Analysis JSON
      ▲ Layer 1                              ▲ Layer 2
      deterministic, free                    AI judgment, costs tokens
      catches known patterns                 catches what parser missed
```

**Layer 1 — Parser** (`app.py`, `_extract_counterparty` function):
- Runs keyword matching on raw transaction descriptions
- Labels transactions into buckets: `BULK SALARY`, `BANK FEES`, `FD/INTEREST`, `LHDN`, `KWSP`, `SOCSO`, `HRDF`, `LOAN DISBURSEMENT`, `RETURNED CHEQUE`, `REVERSAL`, `CASH DEPOSIT`, `CASH WITHDRAWAL`, etc.
- This is the PRIMARY classification — deterministic, instant, no AI cost

**Layer 2 — AI Classification Rules** (`CLASSIFICATION_RULES_v3_3.json`):
- Keywords in `keywords[]` arrays guide the Claude AI when it processes the `full_report.json`
- The AI uses these as deterministic anchors plus applies judgment for edge cases
- This is the SAFETY NET — catches what the parser couldn't label

**When adding a keyword, update BOTH layers.** The parser and the rules file must stay in sync.

## Corpus for testing

**Use raw `full_report.json` files** from `validation runs - json/claude ai prompt file/Full Report Sample/`. These are the parser output — the actual transaction descriptions the keywords need to match against.

Do NOT test against AI analyzed JSONs (those are outputs, not inputs).

Drop as many `full_report.json` files as possible across different banks. More files = more patterns discovered = better cross-bank coverage.

If no file is present, stop and tell the user to drop one in.

## One iteration = one bank × one category

Pick the next unprocessed (bank, category) pair. Category priority order: **C11 → C05 → C10 → C06/C07/C08/C09 → C12 → C24 → CP1-CP11 → everything else**.

### Step 1: load corpus + rules
- Read the first `full_report.json` whose bank hasn't been fully processed for this category yet.
- Read `CLASSIFICATION_RULES_v3_3.json` → extract the `keywords[]` and `exclusions[]` arrays for the target category.
- Read `app.py` → find the corresponding `_extract_counterparty` pattern block for this category.

### Step 2: find candidates
Filter transactions by side (DR/CR per `side` field in rules). Exclude those already matching any existing keyword (case-insensitive substring).

Group the remainder by a "stem" — first ~90 chars of description, with long digit runs collapsed to `####`. Report the top 20 stems by frequency.

### Step 3: shortlist genuine patterns
Apply heuristics for the target category. For C11 (loan repayment):
- Must contain a loan-related term: LOAN, FINANC, INSTAL, REPAY, `LN ` (word-bounded), HP, HIRE PURCHASE.
- Exclude: CREDIT CARD / CC payments (→ C24 or direct debit, not C11), supplier IBG transfers, inter-account sweeps.

Reject patterns that would match the category's `exclusions[]` entries.

### Step 4: propose diff
Show the user:
1. Transactions currently uncaught (count + sample descriptions)
2. Proposed keyword additions (specific multi-word phrases, not short generic tokens)
3. A risk note per keyword — "could falsely match X" if any ambiguity
4. **Both files to edit**: `app.py` pattern + `CLASSIFICATION_RULES_v3_3.json` keyword

### Step 5: validate before applying
Before editing, grep the proposed keyword against ALL available corpus files:
- Confirm true positives (correct category, correct DR/CR side)
- Confirm zero false positives across all banks
- Test against TC01–TC34 test cases in the rules file
- Run `python scripts/validate_reference_statements.py` to verify no parser regressions

### Step 6: apply on approval
When the user says "yes" or "apply":
- Edit `app.py` — add to the appropriate regex in `_extract_counterparty`
- Edit `CLASSIFICATION_RULES_v3_3.json` — append to `keywords[]`, update `regex` field
- Do NOT commit to git automatically — let the user review before committing

### Step 7: regression test
After applying:
```bash
python scripts/validate_reference_statements.py    # all banks — must be identical to baseline
python scripts/audit_all_banks.py                   # grades — must not degrade
```

### Step 8: advance loop
Move to the next (bank, category) pair. Use ScheduleWakeup with `delaySeconds: 1200` and the same `/loop improve keywords` prompt.

## Keyword safety rules

1. **Cross-bank only** — keywords must work across ALL banks. Use `bank_patterns{}` in the rules file for bank-specific logic, not the general `keywords[]` array.
2. **Multi-word preferred** — short tokens (< 4 chars) risk substring collisions (e.g. `SCF` alone could match reference numbers).
3. **Validate both directions** — confirm true positives AND check for false positives on wrong DR/CR side.
4. **Update regex too** — when adding to `keywords[]` in the rules, also update the corresponding `regex` field.
5. **Keep parser and rules in sync** — every keyword in the rules should also be in the parser's `_extract_counterparty` patterns.

## Parser counterparty labels ↔ category mapping

| Parser label | Category | Side |
|---|---|---|
| `BULK SALARY` | C05 | DR |
| `KWSP` | C06 | DR |
| `SOCSO` | C07 | DR |
| `LHDN` | C08 | DR |
| `HRDF` | C09 | DR |
| `LOAN DISBURSEMENT` | C10 | CR |
| `FD/INTEREST` | C12 | CR |
| `REVERSAL` | C13 | CR |
| `RETURNED CHEQUE` | C14/C15 | DR/CR |
| `INWARD RETURN` | C16 | CR |
| `CASH DEPOSIT` | C17 | CR |
| `CASH WITHDRAWAL` | C18 | DR |
| `Unidentified (Cheque)` | C19/C20 | CR/DR |
| `BANK FEES` | C24 | DR |

## Stop conditions
- No more unprocessed corpus files
- User says "stop"
- Current category has 0 candidates on 3 consecutive banks

## Context management
If context usage exceeds 70%, stop and tell the user to start a fresh session with this same prompt. Pass no state between sessions — each iteration is idempotent because the corpus files + rules file are the source of truth.

## Non-goals (do not touch)
- Individual bank parser modules (`maybank.py`, `cimb.py`, etc.) — those are for `fix_bank_parser.md`
- Schema structure in `BANK_ANALYSIS_SCHEMA_v6_3_3.json` (descriptions OK, field shape NOT)
- Classification *logic* (priority order, dual-tagging, cross-refs) — only the `keywords[]` and `examples[]` arrays
- C01/C02 own-party matching (driven by company_name, not keywords)
- `SYSTEM_PROMPT_v3_5_2.md` — prompt changes are a separate track
