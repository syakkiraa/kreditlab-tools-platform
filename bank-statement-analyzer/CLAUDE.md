# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run the main Streamlit app
The parser UI is gated by HTTP Basic Auth — both env vars must be set or the app will `st.stop()`:
```bash
export BASIC_AUTH_USER=your_username
export BASIC_AUTH_PASS=your_password
pip install -r requirements.txt
streamlit run app.py
```

### Run the fraud analyzer (JSON consumer)
```bash
streamlit run fraud_app.py
```
It accepts either a raw transactions list or a `full_report.json` exported from `app.py`.

### Parser validation (quick smoke test)
```bash
python scripts/validate_reference_statements.py                 # all banks
python scripts/validate_reference_statements.py --bank Maybank --verbose
```
Reads PDFs from `Bank-Statement/<Bank>/**/*.pdf` and prints counts of zero-tx files, invalid dates, parse errors, schema-key violations, and rows where debit and credit are both positive.

### Parser quality audit (A–F grading)
```bash
python scripts/audit_all_banks.py                # all banks
python scripts/audit_all_banks.py --bank Alliance
```
Outputs `audit_reports/<bank>_quality_report.json` per bank plus a summary `audit_reports/dashboard.json`. Uses `ground_truth.json` (next to each PDF) when present; otherwise derives expectations from the PDF's `TOTAL DEBIT/CREDIT` line. Balance tolerance is `BALANCE_TOLERANCE = 1.00` (ringgit).

### Backfill ground-truth files
```bash
python scripts/extract_ground_truth.py
```
Generates `ground_truth.json` alongside each PDF from the statement's footer totals.

### System deps for OCR / image-only PDFs
`packages.txt` pins `libpoppler-dev`, `poppler-utils`, `tesseract-ocr`. Install these on Linux hosts (Railway handles it automatically).

## Architecture

### High-level flow
1. **`app.py`** (Streamlit) accepts PDF uploads, dispatches each file to the correct bank parser based on the user's bank selection, and collects rows.
2. Each parser returns `List[Dict]` of raw transactions.
3. `core_utils.normalize_transactions()` maps every row to the canonical schema and `dedupe_transactions()` drops duplicates.
4. Optional: `pdf_fraud_detector.analyze_pdf()` runs BEFORE extraction on the raw bytes to flag integrity issues — it always flags, never blocks.
5. The UI exports the combined result as CSV/XLSX/JSON, or as a `full_report.json` that `fraud_app.py` can ingest.

### Canonical transaction schema (enforced by `core_utils.ensure_transaction_schema`)
```
{ date (ISO YYYY-MM-DD), description, debit, credit, balance|None,
  page|None, bank, source_file }
```
Invariants worth knowing before editing parsers:
- `debit` and `credit` are **non-negative**; for any row one of them is zero. Parsers returning a signed amount get auto-flipped by `ensure_transaction_schema` — don't rely on that, emit the correct side.
- Balance is allowed to be `None` (e.g. footer rows, missing column).
- Extra parser-provided scalar metadata (e.g. `account_no`, `company_name`, `seq`, `transaction_date`, `time`) is preserved through normalization; `account_no` / `account_number` are harmonized both ways.
- Fingerprint for dedupe = `date|description|debit|credit|balance|bank` (see `transaction_fingerprint`).

### OD (overdraft) balance sign convention
Every modern parser (Maybank, Ambank, Alliance, Bank Rakyat, Hong Leong, UOB, plus CIMB Islamic / Maybank Islamic on bank-emitted OD shapes) emits OD balances **signed-negative** — an overdrawn balance is a negative number, and the trail follows the CR formula `prev + CR − DR`. Alliance was on a positive-magnitude convention before 2026-04-20 (`prev + DR − CR`); the switch happened when the parser was rewritten to do per-row signed-balance math. Some historic JSONs in `Bank-Statement/Alliance/` may still carry the legacy convention.

The Track 2 engine (`kredit_lab_classify_track2.py:_build_monthly_for_account` and `_compute_opening_from_row`) auto-detects convention per-account from the sign of `opening_balance`: positive → legacy formula, zero-or-negative → CR formula. Flag 14 (OD high-utilisation) uses `abs(closing_balance)` so it works under either convention. Track 1 still hard-codes the positive-magnitude formula.

When fixing balance-trail bugs or reviewing `audit_reports/*.json`, sign-convention mismatches were historically the #1 source of false positives. The Track 2 engine now handles both transparently; audit anomalies that survive convention-correct math are real extraction gaps.

### Per-bank parser modules
14 single-purpose modules, one per bank: `maybank.py`, `public_bank.py`, `rhb.py`, `cimb.py`, `bank_islam.py`, `bank_rakyat.py`, `hong_leong.py`, `ambank.py`, `bank_muamalat.py`, `affin_bank.py`, `agro_bank.py`, `ocbc.py`, `uob.py`, `alliance.py`. Each exposes one entry point (e.g. `parse_transactions_maybank`, `parse_ambank`, `parse_transactions_alliance`) whose signature varies — some take `pdf_input: bytes`, some take an already-opened `pdfplumber.PDF`. See the `PARSERS` dispatch tables in `scripts/validate_reference_statements.py` and `scripts/audit_all_banks.py` for the canonical call shape per bank.

Parsers mostly use `pdfplumber`; `pdf_fraud_detector.py` and `maybank.py` additionally use `PyMuPDF` (`fitz`). Some formats (Affin, Bank Islam) have OCR-fallback code paths triggered when the text layer is empty.

Affin has two bank-specific helpers in `core_utils.py` that other banks must NOT call: `dedupe_transactions_affin` (keys on amount+balance, not description — description strings vary across OCR runs) and `filter_affin_balance_outliers` (drops OCR-extra-digit balances ±1.5M from the median).

### PDF integrity detector (`pdf_fraud_detector.py`)
8 layers: metadata, fonts, text-layer anomalies, visual render hashes, PyMuPDF↔pdfplumber cross-validation, bank-profile fingerprint, structural, arithmetic balance trail. Plus `compare_batch()` for multi-file uploads. Known legitimate server-side PDF generators (iText, ReportLab, wkhtmltopdf, JasperReports, etc.) are listed in `_EDITOR_SIGNATURES` context — do not add them to the editor signatures list or every bank PDF will flag.

### Sample corpora
- `Bank-Statement/<Bank>/...` — ground-truth reference PDFs used by the validate/audit scripts. Keep new samples under the matching bank folder; scripts discover PDFs recursively.
- `BS-Example/` — additional examples.
- `validation runs - json/` — Streamlit `full_report.json` exports kept for the classifier-keyword improvement loop. The classification rules file itself is `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_3.json`.

### Workflow prompts under `prompts/`
- `fix_bank_parser.md` — per-bank parser repair workflow (reads audit report, fixes one bank in isolation, does not touch shared utils).
- `improve_keywords.md` — classifier-dictionary improvement loop. Only edits `keywords[]` / `examples[]` in `CLASSIFICATION_RULES_v3_3.json`; never edits parser `.py` files or the schema.
- `run_audit_loop.md`, `NEXT_CHAT_PROMPT.md` — session-bootstrap prompts.

### Deployment
`Procfile` targets Railway: `streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT --server.headless=true`. Python 3.10+, and `BASIC_AUTH_USER` / `BASIC_AUTH_PASS` must be configured in the Railway env.
