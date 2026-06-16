# Fix parser for {BANK}

You are improving the bank statement parser for **{BANK}**. You work in isolation
— only touch files for this bank. Do NOT modify other banks' parsers or shared
utilities unless the quality report explicitly says a shared bug affects this bank.

## Inputs you will receive

1. **Parser file**: `{BANK_PARSER_FILE}` (e.g. `alliance.py`, `cimb.py`)
2. **Quality report**: `audit_reports/{BANK}_quality_report.json` — per-PDF grades,
   balance/direction/description issues, pattern-match proxies
3. **Sample PDFs**: `Bank-Statement/{BANK}/**/*.pdf`
4. **Ground truth**: `Bank-Statement/{BANK}/**/ground_truth.json` (PDF totals the
   parser MUST match). If absent for a PDF, derive expectations from the PDF's
   TOTAL DEBIT/CREDIT line before grading.
5. **Classifier spec**: `SYSTEM_PROMPT_v3_5.md` — the downstream consumer. The
   parser MUST output transactions with fields: `date, description, debit, credit,
   balance, bank, source_file`. Descriptions are customer-perspective.

## Order of operations (do not skip)

### Step 1 — Read the quality report and understand what's failing
Open `audit_reports/{BANK}_quality_report.json` and list every distinct bug:
- Balance trail failures → which PDFs, what delta
- Direction mismatches → columns are swapped (see Bug Class B below)
- Description issues → footer contamination, zero amounts, truncated names
- Missing pattern coverage → raw descriptions not being parsed to counterparties

Do NOT start fixing yet. Write a plan first.

### Step 2 — Verify against the actual PDF
For the worst-grade PDF, open it with `pdfplumber` and compare a handful of
transactions to the parser output. Confirm the bug class before editing code.
A "balance fail" can be caused by (a) a genuine extraction gap, (b) a DR-balance
formula mismatch, (c) a column swap, or (d) ground truth being wrong — all four
need different fixes.

### Step 3 — Apply ONE bug class at a time, rerun audit, verify

```
python scripts/audit_all_banks.py --bank {BANK}
```

After each fix:
- The target bug should disappear or shrink
- `grade` should improve or stay the same (never degrade)
- `total_transactions` should stay within ±1% of the prior run (unless the fix is
  explicitly about recovering missed transactions)

### Step 4 — Regression check across all banks
Only after the target bank's grade is improved:

```
python scripts/audit_all_banks.py
```

If any OTHER bank's grade dropped, revert your last change and isolate. Shared
utilities (`core_utils.py`, `app.py` counterparty extractors) can cause
cross-bank regressions — be especially careful there.

## Bug classes and how to fix each

### A. Footer / boilerplate leaking into descriptions
Bank statements repeat a disclaimer at page breaks. It concatenates onto the last
transaction's description. Fix: add a regex strip to the parser's description
cleanup step.

Pattern (Alliance example, generalize for this bank):
```python
FOOTER = re.compile(
    r"\s*(?:The items and balances shown above|Segala butiran dan baki akaun).*$",
    re.IGNORECASE | re.DOTALL,
)
desc = FOOTER.sub("", desc).strip()
```

Find the bank's actual footer text by reading one of its PDFs. Don't copy
Alliance's regex verbatim if this bank uses different wording.

### B. Credit/debit column swap (CRITICAL — silent bug)
Symptom: `balance_detail` says "columns are SWAPPED" or transaction amounts land
in the wrong field. Common trigger: **DR-balance accounts** (overdraft, revolving
credit) where balance increases mean the customer owes more.

Detection signals:
- Every balance has a "DR" suffix (e.g. "1,772,795.42 DR")
- Account type contains "BIZ REF PROG", "OVERDRAFT", "OD", "REVOLVING"
- Portfolio summary shows "Total Borrowings"
- Standard formula `opening + cr - dr = closing` fails, but inverted formula
  `opening - cr + dr = closing` succeeds

Fix principle: for DR-balance accounts, trust the PDF's actual column positions
(PDF "Debit" column = money OUT from customer = parser `debit`). Do NOT use a
balance-trail heuristic to decide which column is which — that heuristic inverts
on DR accounts. Also adjust reconciliation formula conditionally:
```python
if is_dr_balance:
    expected_close = opening - gross_cr + gross_dr
else:
    expected_close = opening + gross_cr - gross_dr
```

### C. Zero-amount transactions
One or more rows with `debit=0` and `credit=0` and a non-balance-row description.
Usually means the amount column wasn't captured on that row. Open the PDF at that
date and check — is the amount actually present? If yes, the regex/column-extract
logic missed it. If no, the PDF row might be a header/footer fragment that should
have been filtered.

### D. Truncated entity names
Banks truncate counterparty text to ~20 chars. Parser should output the raw
description; the classifier (downstream) handles truncation recovery. BUT the
parser must preserve the full text that IS on the page — not accidentally slice
it further. Look for over-aggressive character limits in regex groups (e.g.
`{1,20}` where no limit is needed).

### E. Missing counterparty patterns
If the bank has formats the parser doesn't recognise, add patterns to the bank's
extraction function. Use the v3.5 `missing_bank_patterns[]` format from the spec.

## What NOT to do

- Don't change the parser's output schema (fields: date, description, debit,
  credit, balance, bank, source_file). The classifier depends on this shape.
- Don't edit `scripts/audit_all_banks.py` — the harness is the scoreboard.
- Don't fix bugs in other banks' parsers "while you're there."
- Don't commit if any bank regressed.

## When done

Output a brief report:
- Grade before → after for {BANK}
- List of bugs fixed (one line each)
- Any PDFs still failing and why
- Any cross-bank regressions encountered and how you resolved them
