# Engine Sync Plan — bring the integrated analyzer to v7.9.4 parity

**Status:** the dashboard's vendored analysis engine is stale and is running an **old prompt + old engine**. This note captures the diagnosis and the exact steps to fix it.

## How the integration works

- The dashboard runs its **own copy** of the Python engine under `financial-statement-analysis-logic/`.
- The Next.js server (`lib/server/financial-statement-analysis.ts`) spawns **`analyze.py`** as the engine (the `api.py` in that folder is legacy/unused). `render_bridge.py` is dashboard-only glue (HTML/PDF/Excel) and is intentionally NOT synced.
- The **source of truth** is the standalone repo:
  `/Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for Kredit Lab/Financial Statement Analyzer HTML (Renderer)/repo`
  on the **`v8-api`** branch (the automated PDF→Tensorlake→Claude→render product; it has `analyze.py`).
- `scripts/sync-engine.sh` copies engine files from the standalone repo into `financial-statement-analysis-logic/`. `--check` is a read-only dry run.

## Diagnosis (as of 2026-06-14)

`./scripts/sync-engine.sh --check` reports 2 of 4 files drifted:

| File | State | Detail |
|---|---|---|
| `streamlit_financial_report_v7_7.py` | **stale, 912 lines behind** | Missing the entire financial-consistency validator suite (7 checks: `run_financial_consistency_checks`, `check_balance_sheet_identities`, `check_pnl_chain`, `check_ratio_recomputation`, `check_cross_section_figures`, `check_section_sums`, `check_statement_completeness`) **and** the funding-profile facility-total fix. |
| `analyze.py` | **stale, 14 lines behind** | `FRAMEWORK_PATH` points at `"KreditLab_v7_9 copy.txt"` (legacy ≈ v7.9.2). Should be `KreditLab_v7_9_4.txt`. Also its `run_validators` does NOT call `run_financial_consistency_checks`. |
| `KreditLab_v7_9 copy.txt` | "up to date" but **WRONG FILE** | This legacy frozen prompt matches the standalone copy, but it is not the active prompt. Active = `KreditLab_v7_9_4.txt` (65,955 bytes), which **does not exist** in `-logic/`. |
| `excel_export.py` | up to date | — |

### Root cause of the prompt drift
`sync-engine.sh`'s `FILES` list contains `"KreditLab_v7_9 copy.txt"` — the legacy file — so it will **never** pull `KreditLab_v7_9_4.txt`. Running sync as-is fixes the renderer + analyze.py but **leaves the wrong prompt**. Fix the script first.

## Plan

1. **Fix `scripts/sync-engine.sh`** — in the `FILES` array, replace
   `"KreditLab_v7_9 copy.txt"` with `"KreditLab_v7_9_4.txt"`.
2. **Run the sync:** `./scripts/sync-engine.sh`
   This copies the updated `streamlit_financial_report_v7_7.py` (consistency suite + funding fix), `analyze.py` (FRAMEWORK_PATH → v7.9.4, consistency suite wired into retry loop), and `KreditLab_v7_9_4.txt` into `financial-statement-analysis-logic/`.
3. **(Optional) delete** the now-unreferenced `financial-statement-analysis-logic/KreditLab_v7_9 copy.txt` to avoid confusion (harmless if left).
4. **Parity-test:** run the dashboard's `analyze.py` on the MTC sample and compare to the standalone golden, as per the usual engine workflow. Confirm the engine starts (the prompt file resolves) and the Funding Profile "Term Loan" Total foots to its own split (not the portfolio total).
5. **Commit in this repo + deploy** (Vercel, per `vercel.json`). No dev-server restart needed locally — the engine is spawned fresh each analysis.

## Verify after sync

```bash
# from the dashboard repo root
grep -n 'FRAMEWORK_PATH' financial-statement-analysis-logic/analyze.py     # -> KreditLab_v7_9_4.txt
ls financial-statement-analysis-logic/KreditLab_v7_9_4.txt                 # exists
grep -c 'def run_financial_consistency_checks' financial-statement-analysis-logic/streamlit_financial_report_v7_7.py  # -> 1
./scripts/sync-engine.sh --check                                           # -> all up to date
```

## Notes / open questions

- Confirm `v8-api` is the correct source branch (it is what the dashboard mirrors — automated `analyze.py` pipeline). If the dashboard should track `main` (legacy JSON-only) instead, the source differs.
- The standalone funding-profile fix (per-facility Total derived from its own current+non-current; grand total footed to rendered rows) is already committed on both standalone branches: `v8-api` (`f3adacb`) and `main` (`d5de04f`). It arrives here via step 2.
- Engine version policy: framework prompts are immutable once released; new version = new `KreditLab_v7_9_X.txt` file + bump `FRAMEWORK_PATH`. Keep `sync-engine.sh`'s `FILES` list pointed at the current active prompt file each release (the trap this plan fixes).
