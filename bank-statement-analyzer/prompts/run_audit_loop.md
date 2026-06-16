# Parser audit + fix loop

Re-audit all bank parsers and fix any regressions. Do not deviate from these steps.

## Steps

1. Run: `python3 scripts/audit_all_banks.py`
2. Read `audit_reports/dashboard.json`. For any bank graded C/D/F (ignore SCANNED),
   open `audit_reports/<bank>_quality_report.json`.
3. For each failing PDF, follow `prompts/fix_bank_parser.md` exactly:
   - identify bug class (A footer / B column-swap / C zero-amount / D truncation / E missing patterns)
   - verify against the actual PDF with pdfplumber before editing
   - fix ONE bug class, rerun `--bank <X>`, confirm grade improved
   - then rerun full audit for cross-bank regression check
4. Do NOT modify `scripts/audit_all_banks.py` (the scoreboard) or other banks' parsers.
5. Report: grade before → after per bank, bugs fixed, any PDFs still failing and why.

## Grading reference

- **A** — balance pass, no column swap, ≤5 desc issues, ≥80% non-empty descriptions
- **B** — ≤20 issues OR ≥60% non-empty
- **C** — ≤50 issues OR ≥40% non-empty
- **D** — ≤100 issues OR ≥20% non-empty
- **F** — worse, OR balance trail fails, OR column swap, OR parser crashed
- **SCANNED** — 0 tx, no crash (image-only, needs OCR — not a parser bug)

Description issues = footer_contamination + zero_amount + missing_description + both_sides_positive.
Truncation is tracked but not graded (bank-side, not parser).

## Parallel mode

To fix multiple banks concurrently, spawn one Agent per failing bank with this prompt,
substituting `{BANK}` throughout `prompts/fix_bank_parser.md`. Each agent works in
isolation on its own bank's parser only.

## Current baseline (2026-04-15)

13/14 banks A, AffinBank SCANNED (image-only), Maybank B (9 desc issues / 16,742 tx).
Ground truth coverage 2/216 PDFs — grades are heuristic-only without GT.
