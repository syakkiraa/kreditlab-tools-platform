# HANDOVER — Kredit Lab Financial Statement Analyzer

Last updated: 2026-06-02 (session 2b — Railway font polish, Inter font live in production)

## TL;DR for the next session

The v8 pipeline now runs **PDF → Tensorlake OCR → Claude API → renderer** end-to-end.
Tensorlake is wired into `streamlit_app_v8.py` as a new PDF upload path with a
cost gate, markdown preview/download, then the existing Claude pre-flight.

**Railway PDF rendering is now premium-quality** — Inter font (full weight range
100–900), Noto Color Emoji (colorful icons), DejaVu Sans Mono (table numbers).
User confirmed visual quality on 2026-06-02 after testing both HuaHub + MTC on
production. PDF font/emoji fix was a Dockerfile change (`fonts-inter`, `fc-cache -fv`,
`fonts-noto-color-emoji`, `fonts-dejavu-core`) plus a one-line CSS change to put
Inter first in the font-family chain.

**Branches are intentionally dual-system** — `main` is the standalone JSON-only
legacy product, `v8-api` is the automated API product. **They will NOT be merged.**
Both branches keep the renderer CSS in sync (Inter preference + legacy DYLD preamble).

**Budget remaining (2026-06-02):** ~$1.76 Anthropic (started $4.08, spent $2.32 on
parity testing), $0.40 Tensorlake spent on HuaHub OCR (40 pages × $0.01). No
additional spend during session 2b (font work was all Dockerfile/CSS, no API calls).

**Outstanding next-session items, priority order:**
1. **Add `TENSORLAKE_API_KEY` to Railway Variables** (user action — production
   PDF *upload* path is blocked until this is set; .txt and .json paths work).
2. **Rotate Tensorlake key** after step 1 verification — original was pasted in
   chat history and is compromised.
3. **DSCR cross-section consistency validator** — confirmed broken live on HuaHub
   (1.81x in ratios table vs 1.86x in DSCR section). Code change to `analyze.py`.
4. **Rotate ANTHROPIC_API_KEY** — same hygiene as Tensorlake, still pending.

---

## The pipeline (CURRENT)

```
Step 1   PDF ─► Tensorlake OCR ─► markdown      (AUTOMATED via tensorlake_ocr.py)
Step 2   markdown OR .txt ─► Claude API + v7.9 framework ─► JSON      (analyze.py)
Step 3   JSON ─► renderer ─► HTML / PDF / Excel                       (existing)
```

The v8 Streamlit app accepts **three** upload types:
- `.pdf` → Tensorlake OCR (cost gate) → markdown preview/download → Claude pre-flight (cost gate) → analyze → render
- `.txt` → Claude pre-flight (cost gate) → analyze → render (existing flow)
- `.json` → renderer (skip both APIs; existing flow)

The user can **download the OCR'd markdown** as `.md` (or `.zip` for multiple) and
re-upload it later as `.txt` to skip Tensorlake entirely — saves money on re-renders.

---

## Where everything lives

### Dual-branch architecture (CRITICAL)

| Branch | Purpose | Active Streamlit app | Railway? |
|---|---|---|---|
| `main` | **Legacy product** — standalone JSON-only renderer | `streamlit_financial_report_v7_7.py` | No |
| `v8-api` | **Automated product** — full PDF/TXT/JSON pipeline | `streamlit_app_v8.py` | Yes |

User has decided **NOT to merge `v8-api` → `main`**, depending on business growth.
Both branches will be maintained in parallel as distinct products.

**Implications when fixing shared code (`streamlit_financial_report_v7_7.py`, which
also defines the shared renderer functions): apply the fix to BOTH branches.**
The legacy DYLD-preamble fix from 2026-06-01 was done this way: `main` commit
`b795bc8`, `v8-api` commit `c4b6fae`.

### Code (all in `repo/`)

| File | Purpose | Branch availability |
|---|---|---|
| `streamlit_app_v8.py` | v8 UI: .pdf / .txt / .json upload, OCR + Claude cost gates, streaming progress, sidebar telemetry | v8-api only |
| `analyze.py` | Claude API engine: framework caching, doc caching, validation loop, cost guardrails, 4-layer ftfy defense | v8-api only |
| `tensorlake_ocr.py` | Tensorlake SDK wrapper: `count_pdf_pages()` (free, pypdf) + `ocr_pdf_to_markdown()` (Tensorlake call). Also a CLI for batch OCR | v8-api only |
| `streamlit_financial_report_v7_7.py` | Legacy app + shared renderer (`generate_full_html`, `convert_html_to_pdf`, etc.) | **both branches** — keep in sync on shared-code fixes |
| `render.py` | CLI wrapper around the renderer (no Streamlit needed) | v8-api |
| `excel_export.py` | Excel writer | both |
| `KreditLab_v7_9 copy.txt` | Framework system prompt. Mojibake-cleaned (backup at `.bak`) | v8-api |
| `Dockerfile` | Railway deployment. `CMD` → `streamlit_app_v8.py` | v8-api |
| `requirements.txt` | `streamlit pandas openpyxl weasyprint anthropic ftfy tensorlake pypdf` | v8-api |
| `samples/muhafiz/` `samples/mtc_engineering/` `samples/huahub_marketing/` | Parity test fixtures (.txt + golden JSON). DO NOT delete | v8-api |
| `samples/.runs/` | Per-run cost logs (gitignored). Sidebar reads from here | v8-api |

### Git / GitHub

- Repo: **https://github.com/luqman196/financial-statement-analysis**
- `main` head: `c5e03ea` — `fix: prefer Inter font in legacy renderer CSS`
- `v8-api` head: `a1a6584` — `feat: prefer Inter font for premium PDF look on Railway`
- v8-api is 10 commits ahead of main. Intentional — see Dual-branch architecture above.

### Deployment

- Railway service: `financial-statement-analysis`
- Public URL: `financial-statement-analysis.kreditlab.my`
- Deployed branch: `v8-api` (auto-deploys on push)
- Required env vars in Railway → Variables tab:
  - `ANTHROPIC_API_KEY` — ✅ set
  - `TENSORLAKE_API_KEY` — ⚠️ **NOT YET SET (next-session task #1).** Without it, .pdf uploads error out with the "🔴 not set" message; .txt and .json paths still work
  - `APP_USERNAME`, `APP_PASSWORD` — set for auth
- PDF/Excel libs installed via `Dockerfile` apt-get block (`libpango`, `libcairo`, `fontconfig`)
- **Font stack** (live on Railway as of 2026-06-02): `fonts-inter` (Inter — full 9 weight variants, the premium primary), `fonts-liberation`, `fonts-dejavu-core` (sans-serif fallbacks), `fonts-noto-color-emoji` (colorful 🏦 📊 etc. icons), `fonts-symbola` (monochrome emoji fallback). **`fc-cache -fv` runs after install** — without it, `python:3.11-slim-bookworm`'s post-install hook doesn't run and weasyprint can't find any of the fonts at runtime (resulted in DejaVu Serif fallback that user flagged as "ugly")

### Local environment (luqman's Mac)

- `~/.zshenv` → exports for `ANTHROPIC_API_KEY` and `TENSORLAKE_API_KEY`
- Homebrew at `/opt/homebrew`; Pango installed via `brew install pango`
- **Python 3.11 via Homebrew** (`/opt/homebrew/bin/python3.11`) — required by tensorlake SDK (`>=3.10`)
- pip 3.11 packages: `streamlit`, `pandas`, `openpyxl`, `weasyprint`, `anthropic`, `ftfy`, `tensorlake`, `pypdf`
- Old Python 3.9 (Apple CLT) still works for the legacy app but NOT for `streamlit_app_v8.py` because of the tensorlake import.

### Running locally

```bash
# Always source Homebrew shellenv first (so python3.11 is on PATH)
eval "$(/opt/homebrew/bin/brew shellenv)"

# v8 app (PDF/TXT/JSON pipeline)
cd "/path/to/repo"
python3.11 -m streamlit run streamlit_app_v8.py
# → http://localhost:8501 (or whatever port)

# Legacy app (JSON-only) — runs on either Python, 3.11 preferred
python3.11 -m streamlit run streamlit_financial_report_v7_7.py --server.port 8512

# Engine alone (CLI)
python3.11 analyze.py samples/huahub_marketing/*.txt --model opus --strict --out /tmp/out.json

# Tensorlake OCR alone (CLI, batch)
python3.11 tensorlake_ocr.py path/to/file.pdf --out-dir /tmp/md/
```

---

## Key design decisions (with rationale)

1. **Dual-system, no merge** — `main` = legacy JSON-only product; `v8-api` = automated product. Maintained in parallel. Business may rely on one, the other, or both.
2. **Hybrid Tensorlake architecture** — Streamlit accepts PDF *or* .txt; PDF goes through OCR + preview before the Claude cost gate fires. Users can edit the markdown or download it for later re-upload without re-paying Tensorlake.
3. **Tensorlake markdown fed directly to `analyze.py`** — no markdown→plain-text shim needed. Path-A test on HuaHub showed identical 9/11 parity to hand-OCR'd .txt. The v7.9 framework parses markdown headings + pipe tables without regression on Opus. ([Tensorlake offers markdown only — no plain-text mode in the API.](https://docs.tensorlake.ai/document-ingestion/parsing/read))
4. **Tensorlake SDK call shape** — `doc_ai.upload(path) → file_id`, then `doc_ai.parse_and_wait(file_id=file_id, parsing_options=ParsingOptions(...))`. **NEVER use `file=` (deprecated** — mis-detects path as raw_text).
5. **Default model: `claude-opus-4-7` with `--strict`** — best parity vs golden, ~$0.55–$1.02 per company depending on document size.
6. **`--no-thinking` recommended** — adaptive thinking burns the output token budget before JSON completes.
7. **No assistant-turn prefill** — 4.6/4.7 models reject it (400). JSON output forced via system-prompt instruction at the END (after strict-mode `COMPLETENESS_RULES`).
8. **Two cache breakpoints** — system prompt (framework) + user turn (documents). Validation retries reuse both at ~10% cost.
9. **Pre-flight cost gate ALWAYS shown** before any Anthropic spend (and now also before any Tensorlake spend on the PDF path).
10. **4-layer ftfy defense against mojibake** — framework load, input file load, JSON output extraction, JSON disk write (with `ensure_ascii=False`).
11. **Mac weasyprint preamble in BOTH Streamlit apps** — `os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib:..."` at the top, before importing streamlit. Without it, weasyprint can't find Pango on Mac → PDFs come out in serif. darwin-only check, harmless on Linux/Railway.
12. **`v7_7` file additions** — non-breaking: (a) `generate_ma_limitations_section()` returns empty when key absent; (b) DYLD preamble at top, darwin-only.
13. **Lifetime cost telemetry** — reads `samples/.runs/*.json`. CLI and Streamlit both log there in same format.

---

## Parity baseline (locked 2026-06-01)

| Company | Model | Strict | Source | Spot-checks | Notes |
|---|---|---|---|---|---|
| MTC Engineering | Opus 4.7 | ✅ | Hand-OCR .txt (2024 audit + 2025 BS+P&L) | **9/11** | Name casing on `legal_name` (Title Case vs all caps); CCC integer rounding |
| HuaHub Marketing | Opus 4.7 | ✅ | Hand-OCR .txt (2024 audit + 2025 mgt acc) | **9/11** | Revenue/DSCR/CCC integer rounding |
| HuaHub Marketing | Opus 4.7 | ✅ | **Tensorlake markdown** (2 PDFs, 40 pages) | **9/11** | Same diffs as hand-OCR — proves Path A works |
| Muhafiz Security | Opus 4.7 | ✅ | Hand-OCR .txt (older session) | golden | Original baseline |

**All FY2024 financial figures match to the cent** across all four runs (Revenue, GP, NPAT, EBITDA, Total assets, Total equity, Current ratio, DSCR). Differences are all cosmetic rounding or casing.

---

## Open items / what's next (priority order)

### A — Highest priority

1. **[user] Set `TENSORLAKE_API_KEY` in Railway Variables.** Production PDF upload won't work otherwise. Use the existing key for now, rotate after step 2.
2. **[user] Verify PDF flow in production** — visit `financial-statement-analysis.kreditlab.my`, upload a small PDF (e.g., HuaHub mgt acc, 3 pages = $0.03 OCR), confirm the OCR gate, preview, and Claude pre-flight all render.
3. **[user] Rotate Tensorlake API key** — original is in chat history (compromised). Generate new at Tensorlake console → update `~/.zshenv` + Railway Variables → revoke old.
4. **[code] DSCR cross-section consistency validator in `analyze.py`** — confirmed broken live on HuaHub Tensorlake run: `financial_ratios.leverage_ratios.dscr` = 1.81x but `dscr_analysis.calculation.{period}.dscr` = 1.86x (hand-verified 1.86 is correct). Add a validator that diffs the two fields per period and feeds mismatches into the existing self-correction loop. ~50 LOC. Test cost: ~$0.20 re-running Muhafiz on Opus strict with `--max-retries 2`. Also probably fixes MTC's similar drift.

### B — Maintenance

5. **[user] Rotate `ANTHROPIC_API_KEY`** — same hygiene reason. Generate new → update `~/.zshenv` + Railway → revoke old.
6. **Railway persistent volume for `samples/.runs/`** — lifetime sidebar stats reset on each Railway redeploy. Mount a volume so they survive.
7. **History table in sidebar** — expandable panel showing last N runs (date, model, company, cost, validation status). Reads from `samples/.runs/*.json`.

### C — Future enhancements (not urgent)

8. **MA Limitations renderer fallback** (optional) — for old JSONs lacking `_ma_limitations`, synthesize a default placeholder panel so the orange box still appears. User has currently de-prioritised this ("secondary").
9. **Test on Muhafiz PDFs via Tensorlake** — Muhafiz audit + 2 management-account PDFs available in `repo/Sample Case/Audited Account + Management Account/`. Would validate the full PDF→render flow on a 3rd company. Cost ~$1.40 (OCR + Claude).
10. **Async/job-queue model** — current Streamlit synchronous-with-spinner pattern blocks one user at a time. Fine for internal use; switch to async if multiple concurrent users matter.
11. **Framework v8 of KreditLab framework** — current prompt was tuned for web-Claude; some instructions land softer through the API. Eventual rewrite would improve parity further.
12. **Model upgrade procedure** — when Anthropic releases Opus 4.8 / 5.0, update `MODEL_ALIASES` + `PRICING` in `analyze.py`, run parity test against Muhafiz golden, promote if it matches/beats. ~30 min effort.

---

## Cost / budget tracking

- **Anthropic** trial budget: $10
  - Spent across both sessions: ~$6.32
  - Remaining: **~$1.76** (verify against console — user reported $4.08 starting balance for session 2)
- **Tensorlake**: no explicit cap set
  - Spent: **$0.40** (HuaHub OCR, 40 pages × $0.01)
  - Pricing: $0.01/page, $10/1000 pages
- **Per-company cost going forward** (Tensorlake + Anthropic combined, Opus strict, no-thinking):
  - Small company (~20 pages, simple statements): ~$0.80–$1.00
  - Larger company (~40 pages, full audit): ~$1.40–$1.80

---

## Known quirks / gotchas

- **Python 3.11 is required** for the v8 app locally — tensorlake SDK constraint. Use `python3.11 -m streamlit run streamlit_app_v8.py`, never plain `python3` (which is 3.9 on Apple CLT). Source `eval "$(/opt/homebrew/bin/brew shellenv)"` first to put 3.11 on PATH.
- **Tensorlake API: `file=` is deprecated** — use `upload(path) → file_id`, then `parse_and_wait(file_id=...)`. The `file=` parameter mis-detects paths as raw_text and raises a misleading "mime_type must be provided when raw_text is used" error.
- **Tensorlake page count via `parsed_pages_count` is unreliable** — falls back to `len(result.pages)` in `tensorlake_ocr.py` for cost reporting.
- **PDF "cannot download" locally** = weasyprint can't find Pango. Both Streamlit apps now set `DYLD_FALLBACK_LIBRARY_PATH` automatically. Only matters for ad-hoc scripts that import weasyprint without going through one of the apps.
- **adaptive thinking on Sonnet** burned all 32k output tokens on reasoning, never emitted JSON. Always use `--no-thinking` for now.
- **Streamlit deprecation warning** about `st.components.v1.html` (will be removed after 2026-06-01) — comes from the legacy renderer file. Functional but should be migrated to `st.iframe` eventually.
- **`legal_name` casing drift on MTC** — Opus rendered "MTC Engineering Sdn. Bhd." in Title Case for both `name` AND `legal_name` fields, but the source documents have `legal_name` as "MTC ENGINEERING SDN. BHD." (all caps). HuaHub got this right. Cosmetic; fixable via stricter framework instruction.
- **Mojibake** — already defused by 4-layer ftfy. Don't worry unless someone edits the framework file on Windows in a misconfigured editor.

---

## How to resume in a new chat

Paste this into the new chat:

> I'm continuing work on the Kredit Lab Financial Statement Analyzer. Read
> `/Users/luqmanulhaqeemmdfauzi/Documents/Project Development Software for
> Kredit Lab/Financial Statement Analyzer HTML (Renderer)/repo/HANDOVER.md`
> for the full context. Today I want to work on [open item from section A or B].

The new Claude will read the file, check the git/Railway state (both `main` and
`v8-api` heads), and pick up where we left off. **Remember: dual-system, no merge.**
