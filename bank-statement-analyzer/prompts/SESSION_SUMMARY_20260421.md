# Session Summary — 21 Apr 2026

Paste this into a fresh Claude Code session after the laptop restart.

---

## Context

Repo: `Bank-Statement-Analysis-main 3`, branch `main`. Today is 2026-04-21.

Parser stack v6.3.3 + classifier prompt stack v3.5.2.

## What shipped this session (5 commits, all pushed)

| Commit | Change | Impact |
|---|---|---|
| `f66c22f` | C06 KWSP CR-side false positives — bare `KWSP` keyword was substring-matching ref codes like `KWSP0559246` in inbound `CR ADVICE` payments from medical TPAs (PM CARE SDN BHD) | **Alliance KYDN: 53 → 0 side mismatches**; real DR-side EPF detections preserved |
| `8972a0d` | C05 `GAJI` / `MENGAJI` substring collision (tuition businesses) + C07 CR-side exclusion for SOCSO/PERKESO refunds | **Maybank Mytutor: 27 → 15 mismatches**; 12 false positives eliminated |
| `b9b153e` | Alliance `IB2G BLKTRF DR CA(M)` bulk-salary + `INSTANT TRANSFER … BACK PAY SALARY` single-person back-pay patterns | **Alliance KYDN: 11 C05 sync gaps → 0**; parser + rules fully synced |
| `250bbbd` | Maybank description extraction — raised y-clustering tolerance 3.0 → 5.0 in `_cluster_lines` to merge misaligned rows where amount/balance and date/description render at slightly different y-coordinates | **Maybank audit B → A**; 8 empty descriptions → real text (`TRANSFER FR AC …`, `CASH DEPOSIT`, cheque refs); 35,413 tx across 75 files preserved |
| `71e763f` | PDF password resolver for offline scripts — `pdf_password_resolver.py` + `.pdf_passwords.json` (gitignored) + patches to `scripts/audit_all_banks.py` and `scripts/validate_reference_statements.py` | BankIslam's 6 F-grade Mytutor PDFs now auto-decrypt with configured password |

## Audit grades snapshot (as of latest run)

| Bank | Grade | Files | Tx | Notes |
|---|---|---|---|---|
| Maybank | **A** | 75 | 35,413 | promoted B → A this session |
| CIMB | A | 55 | 7,446 | clean |
| BankRakyat | A | 54 | 7,182 | clean |
| RHB | A | 44 | 5,556 | clean |
| Alliance | A | 18 | 5,199 | +11 sync gaps closed this session |
| Ambank | A | 30 | 2,741 | clean |
| PublicBank | A | 17 | 1,692 | clean |
| OCBC | A | 12 | 1,179 | clean |
| UOB | A | 12 | 946 | clean |
| HongLeong | A | 17 | 719 | clean |
| BankMuamalat | A | 6 | 447 | clean |
| AgroBank | A | 6 | 414 | clean |
| BankIslam | F | 45 | 726 | 35 A + 4 SCANNED + 6 F (all Mytutor — password-protected — fix ready, needs files) |
| AffinBank | SCANNED | 6 | 0 | OCR-only, deferred |

**System-wide invariants hold**: 0 direction bugs, 0 balance-trail failures, 0 both-DR-and-CR rows across all banks.

## CRITICAL: macOS iCloud keeps evicting files

**Root issue**: the project is under `Documents/` and iCloud Drive's "Optimize Mac Storage" evicts files not recently accessed. This session, the entire `Bank-Statement/` folder vanished **three times** mid-work. Git recovered committed files; **never-committed files are lost**.

**Files confirmed lost (not in git, not on disk)**:
- `Bank-Statement/BankIslam/Mytutor/MY019126 APR25.pdf`
- `Bank-Statement/BankIslam/Mytutor/MY019126 JUN25.pdf`
- `Bank-Statement/BankIslam/Mytutor/MY019126 MAC25.pdf`
- `Bank-Statement/BankIslam/Mytutor/MY019126 MAY25.pdf`
- `Bank-Statement/BankIslam/Mytutor/PW MY019126 JAN25.pdf`
- `Bank-Statement/BankIslam/Mytutor/PW MY019126 FEB25.pdf`
- Some Maybank PDFs (75 → 57 during session; 18 files evicted)

**Fix before next session**: turn off iCloud sync for this folder OR move project out of `Documents/`:
```
System Settings → Apple ID → iCloud → Drive → uncheck "Desktop & Documents Folders"
```
Alternatively: `mv "/Users/.../Documents/Project Development.../" ~/Dev/kredit-lab/`

## Password system — how to use

Already committed and wired. To enable password-protected PDF parsing in offline scripts:

1. Copy `.pdf_passwords.example.json` → `.pdf_passwords.json` (already done — contains `MY019126` for BankIslam Mytutor)
2. `.pdf_passwords.json` is gitignored — stays local only
3. Scripts auto-decrypt when they hit an encrypted PDF

Format:
```json
{
  "Bank-Statement/BankIslam/Mytutor/*.pdf": "password_here",
  "Bank-Statement/SomeBank/Customer/**.pdf": "another_password"
}
```

Fallback: per-file env var `PDF_PASSWORD__<SANITIZED_STEM>` also supported.

## Validator state — remaining gaps (fresh corpus)

From `python3 scripts/validate_keywords.py`, still-open items:

**Side mismatches** (small, mostly accepted):
- Maybank Mytutor: 15 (11 `SALARY` in payer memo fields + 4 `SOCSO`/`PERKESO` CR refunds — AI side-filter covers)
- MBB Naara: 2 (`DEPFACIAL` substring on `EPF` — 1-row edge case, keeping as-is)
- CIMB Muhafiz: 1 (`DUITNOW TO ACCOUNT EPF PAYMENT … MUHAFIZ SECURITY`)
- OCBC Calvin Skin: 1 (`Tax` keyword substring — same class as prior fixes, deferred)
- UOB Juta Kenangan: 1

**Parser sync gaps** (parser missing patterns the rules catch) — NEW TERRITORY:
- Ambank Plentitude C05 (12): `Salary /MISC DEBIT, …, SALARY FEBRUARY`
- Ambank Plentitude C07 (12): `STATUTORY BODY TXN /DEBIT TRANSFER, …, AABEI<digits>`
- Ambank Plentitude C09 (3): `JomPAY /DEBIT TRANSFER, PSMB, <ref>`
- MBB Shahnaz C05 (6): `DUITNOW PAYPRX DR Transfer Funds Salary May25` / `CMS - DR PYMT MARS 5 Interco`
- MBB Shahnaz C08 (3): `DUITNOW PAYPRX DR Transfer Funds LHDN May25`
- Others smaller (Ambank Hon Engineering, Ambank RE Concept, Bank Rakyat, CIMB Naara, HLB MTCE, MBB Hou Tian/Naara/Zaim, UOB Juta/Upell)

## What to do next session (in order)

1. **Fix iCloud first** — otherwise files will keep vanishing. Either disable sync or move the project.
2. **Restore the 6 BankIslam Mytutor PDFs** by re-uploading from original source (wherever you have them). Drop into `Bank-Statement/BankIslam/Mytutor/`.
3. **Verify password flow end-to-end**:
   ```bash
   python3 scripts/audit_all_banks.py --bank BankIslam
   ```
   Expect: BankIslam grade F → A, 6 Mytutor PDFs now parse.
4. **If audit clean** → pick highest-volume parser sync gap (Ambank Plentitude — 27 rows across C05/C07/C09) and close those patterns.
5. **If new issues surface** on refreshed data → keyword loop per `prompts/improve_keywords.md`.

## Key files / commands

| | |
|---|---|
| Authoritative workflows | `prompts/improve_keywords.md`, `prompts/fix_bank_parser.md` |
| Validator (keywords) | `python3 scripts/validate_keywords.py` |
| Parser regression | `python3 scripts/validate_reference_statements.py` |
| Parser audit (A-F grades) | `python3 scripts/audit_all_banks.py` |
| Password config | `.pdf_passwords.json` (local, gitignored) |
| Classification rules | `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_3.json` |
| Fresh test corpus | `validation runs - json/claude ai prompt file/Full Report Sample/*.json` |

## Rules that stuck this session (for AI memory)

- Never commit passwords. `.pdf_passwords.json` is gitignored.
- Short bare keywords (< 5 chars) are dangerous — they substring-match unrelated words. Prefer qualified multi-word variants (`GAJI SEPT`, `KWSP PAYMENT`) + word-boundary regex.
- Statutory categories (C05/C06/C07/C08/C09) are **DR-only by definition**. CR-side references are refunds/claims/revenue, not contributions. Add explicit exclusion notes for AI layer.
- When Maybank rows render with scattered y-coordinates (seen in one APR25 file), clustering at `y_tol=5.0` fixes it cleanly without merging unrelated rows.
