# Parser Bugs Handoff — 2026-05-03 (continues from 2026-05-02)

Hand this to a new chat session as the opening prompt. Continues from
[prompts/PARSER_BUGS_HANDOFF_2026-05-02.md](PARSER_BUGS_HANDOFF_2026-05-02.md)
which was the original D→C re-grade triage.

---

## TL;DR

- All 5 bugs from Kay R quality report are addressed (4 code fixes + 1 verified-no-fix-needed).
- 14-bank validator PASSES. Kay R verified end-to-end via headless re-parse + local Streamlit.
- **Nothing committed. Nothing pushed. Nothing deployed.** All changes sit in working tree on `track-2-development` (wrong branch — they need to move to a Track 1 branch).
- Production (`origin/main` / Railway) is **62 commits behind** `origin/sprint-6/polish` PLUS today's 5 fixes. The merge to main has been gated on BUG-001 being fixed; that gate is now open.

---

## Repo state

| Ref | SHA | Status |
|---|---|---|
| Local current branch | `track-2-development` (`c8b44f8`) | **Working tree dirty: `app.py` + `core_utils.py` modified** |
| `origin/main` (Railway prod) | `a4b2bca` (Sprint 4.5) | NONE of recent fixes; 62 commits behind sprint-6/polish |
| `origin/sprint-6/polish` | `39fa68a` | All Sprint 5/6/7 work pushed; today's 5 fixes NOT here yet |
| `origin/track-2-development` | `c8b44f8` | Track 2 sessions 1+2 (EOD computation, 16-flag reducer). **DO NOT mix parser fixes here.** |

⚠️ Last `git fetch` failed mid-session (port 443 timeout). Numbers above from cache — re-verify with `git fetch origin` before any push.

---

## The 5 fixes done in the 2026-05-02 → 2026-05-03 session (UNCOMMITTED)

### BUG-001 — monthly_summary footer double-counting (HIGH severity, fixed)
- **Files:** `app.py:1090-1342` (Affin/Ambank/CIMB/RHB blocks in `calculate_monthly_summary`)
- **Fix:** replace footer-parsed `total_debit`/`total_credit` with `sum(safe_float(x.get('debit') or 0) for x in txs)`. Default-bank path (Maybank etc.) already used sum-of-rows.
- **Cross-bank scan results (this session):** RHB 7/44 PDFs divergent (6 are Kay R), CIMB 2/37 divergent (1 matches Kay R signature). Affin 0 divergent BUT 6/6 had `None` footers (separate latent gap — see open items). Ambank clean. The fix benefits **RHB and CIMB**, not just RHB.

### BUG-002 — RFLX SC anomaly flagging (HIGH severity, fixed)
- **Files:** `app.py:3196-3220` (SC sub-formats B + D); `app.py:4087-4093` (`RFLX SC ANOMALY (NEEDS REVIEW)` added to `_OWN_PARTY_PROTECTED_LABELS`)
- **Fix:** tighten amount sanity check from `<= RM 100` to `<= RM 1.00` for SC-specific sub-formats only. General bank-fee branch (line 3201) keeps RM 100 cap. Anomalies route to stable bucket `RFLX SC ANOMALY (NEEDS REVIEW)` instead of N raw-description buckets.
- **Mid-session catch:** initially missed a stale `fee_amount_ok` reference at `app.py:3274`, fixed by keeping BOTH variables (`fee_amount_ok` for general fees, `sc_fee_ok` for SC).
- **Impact:** RHB-only. Kay R Aug-15 RM 138,791 was the only anomaly across 263 SC rows in 35 RHB PDFs.

### BUG-003 — SDN BHD suffix normalization (MEDIUM, fixed + extended)
- **Files:** `core_utils.py:1126-1162` (new `normalize_company_suffix` helper); `app.py:4571-4585` (wired into `build_counterparty_ledger` before `_normalise_counterparty`)
- **Fix:** regex tail-strip restoring `SB` / `SDN B` / `SDN BH` / `SDN BHD.` → `SDN BHD`. Extended this session to cover bare `SDN` end too (LAST in alternation order so longest-form matches win).
- **Final regex:** `\b(SB|SDN\s*\.?\s*BHD\.?|SDN\s*\.?\s*BH|SDN\s*\.?\s*B|SDN\.?)\s*$`
- **Cross-bank impact:** 9 of 14 banks affected (RHB, Alliance, Ambank, CIMB, Maybank, OCBC, UOB, Hong Leong, minor PBB). ~60 distinct counterparties benefit from the bare-SDN extension. 22-case test passes. No false positives in 33 cached `Full Report *.json` reports.

### BUG-004 — description-based own-party fallback (MEDIUM, fixed)
- **Files:** `app.py:4252-4297` (new `_description_implies_own_party()` + `_own_party_core_tokens()`); `app.py:4644-4660` (wired into `build_counterparty_ledger`)
- **Fix:** when extracted name doesn't have `(OWN-PARTY)` AND description contains ≥2 holder core tokens (≥50% of holder's distinctive tokens), stamp as `<holder> (OWN-PARTY)`. Catches cases the existing `_strip_own_party_tokens` fast-path misses (single-token extractions like `RESOURCES`, fallback-bucket routings like `UNNAMED RHB TRANSFER (CR)`).
- **Impact:** any bank where holder's name appears in description text.

### BUG-005 — verified, no fix needed
- PyMuPDF coordinate inspection of RHB AUG 2025.pdf (2025-08-27 ghost-verb row) and RHB JAN 2026.pdf (2026-01-23) confirmed: both rows genuinely lack the originator name on the source PDF. Parser's existing continuation-merge captures every line that exists. Routing to `UNNAMED RHB TRANSFER (CR)` is the correct outcome. No code change.

---

## Validation status

- ✅ 14-bank validator passes: 44 RHB / 5,556 tx / 0 parse errors / 0 invalid dates / 0 mis-signed rows
- ✅ Kay R headless re-parse: all 6 months reconcile exactly (Aug DR 988,793.86 / CR 784,870.90 — was inflated +RM 177,122 each side before)
- ✅ Local Streamlit on `http://127.0.0.1:8501` — user verified output is correct
- ✅ 22-case test for `normalize_company_suffix` (truncations + lowercase + false-positive sanity) all pass
- ❗ 6 BankIslam errors in validator are PRE-EXISTING password-protected PDFs (BIMB Mytutor) — not caused by these fixes

---

## What's NOT on main right now

### 62 commits on `origin/sprint-6/polish` not yet merged

Held back per 2026-05-02 handoff: *"Don't merge sprint-6/polish → main until BUG-001 is fixed."* That gate is now open.

Highlights (not exhaustive):
- Sprint 5 #21 V1/V1.1/V2 — `kredit_lab_classify.py` (1,927 lines) ⚠️ see flag below
- Sprint 6 #4/#6/#7/#8/#9/#10/#11*/#16 — Hong Leong, Ambank, OCBC, Alliance, Bank Rakyat, UOB, RHB entity extraction + bucket renames
- Sprint 7 #1–#13 + Phase 0/2A/2B — v3.5.6 slim-down, Bank Rakyat opcode fixes, PBB DUITNOW, BIMB multi-line, BIMB Principal Gas, **parser-wide own-party stamping** (`core_utils.py:842-1024`), statutory side-gate, cheap classifier wins, ambiguous-marker bidirectional exempt + sustained-round RP
- `6afb133` SOCSO regex (KESELAMA + bare PERTUBUH CP)
- `29de7ed` v3.5.2 rules alignment

### Stale .py files on Railway production

```
app.py             +1,779 lines behind   ← biggest gap
core_utils.py      +207 lines behind
kredit_lab_classify.py  +1,927 lines behind   ⚠️ see flag
bank_islam.py      +147 lines behind
alliance.py        +65 / bank_rakyat.py +58 / ocbc.py +55 / maybank.py +54
```

### Stale Track 1 references

```
SYSTEM_PROMPT_v3_5_6.md          831 lines (whole new file)
CLASSIFICATION_RULES_v3_5.json   +26 lines
```

### Plus today's 5 fixes still uncommitted on `track-2-development` working tree

---

## ⚠️ Open flags before any merge to main

1. **`kredit_lab_classify.py` (1,927 lines on sprint-6/polish) is the OLD Track-2 classifier from Sprint 5 #21.** Per the 2026-05-01 architecture decision, the NEW Track 2 lives separately as `kredit_lab_classify_track2.py` on `track-2-development`. Question for next session: **is `kredit_lab_classify.py` imported by `app.py` in the production code path?**
   - If YES → merging sprint-6/polish ships the old Track-2 classifier to Railway, intentional or not.
   - If NO → it's dormant, safe to ship but adds 1,927 lines of unused code.
   - Need to grep before merging.

2. **Affin footer extractor returns `None` for all 6 sample PDFs.** `extract_affin_statement_totals` doesn't find the footer regex on any Affin sample in the corpus. Pre-existing; BUG-001 fix masks it because we now ignore footer anyway. Worth a separate investigation; not blocking merge.

3. **GitHub fetch failed mid-session.** Re-verify origin pointers (`git fetch origin`) before any push.

---

## Pending user decisions

The session ended waiting on these:

1. **Branch choice for committing today's 5 fixes:**
   - **(A)** `sprint-6/polish` — continues Track 1 history; will be in the merge to main
   - **(B)** New branch `parser-bugs-2026-05-03` off `main` — cleaner reviewable PR for just the 5 fixes
2. **Commit shape:** single commit OR 4 separate (one per bug)?
3. **Push timing:** commit-only-no-push for review, OR commit + push together?
4. **Scope of merge to main:** today's 5 fixes only, OR all 62 commits on sprint-6/polish? Bigger merge = more value but more surface to verify.

User has not yet decided any of the above.

---

## Strategic context discussed (no action taken)

- **Track 1 (claude.ai web) inconsistency:** user reports grading varies across runs. LLM non-determinism is fundamental on claude.ai (no temperature/seed control).
- **Recommendation given:** re-grade Kay R **2-3 times** with the NEW parser data BEFORE deciding to accelerate Track 2. Variance was likely data-driven (buggy parser → AI confused by inflated totals, fragmented buckets, mis-routed RM 138K row). 30-min test settles whether to stay on normal Track 2 pace or accelerate.
- **Track 2 status:** sessions 1+2 done (EOD computation port, 16-flag reducer port) on `track-2-development`. ~6-10 sessions remaining per the 2026-05-01 plan. NOT touched in this session.

---

## Hard rules carried over (do NOT violate)

1. **NEVER edit `kredit_lab_classify.py`** from this work (Track 2 isolation, 2026-05-01 architecture).
2. **NEVER edit `prompts/NEXT_CHAT_PROMPT.md`** (Track 2's handoff channel).
3. **NEVER push to remote without explicit user OK.**
4. **14-bank validator must PASS after every parser change.**
5. **No `--no-verify`, no force push, no `--amend` of pushed commits.**
6. **No commits on `track-2-development` for parser/Track 1 work** (user explicit instruction this session).
7. **No SDK / API integration until bank deploy** (per `feedback_no_sdk_until_bank_deploy` memory).

---

## Suggested starting prompt for the new session

> "Read [prompts/PARSER_BUGS_HANDOFF_2026-05-03.md](../prompts/PARSER_BUGS_HANDOFF_2026-05-03.md).
>
> My 5 parser fixes are in the working tree on `track-2-development`. I want them committed on a Track 1 branch and ready to merge to main. Start by:
>
> 1. Confirming git state via `git status` and `git fetch origin`.
> 2. Checking whether `kredit_lab_classify.py` is imported by `app.py` in the production code path (the open flag from yesterday).
> 3. Then propose a branch + commit + push plan for me to approve."

---

## Files relevant to this handoff

- [app.py](../app.py) — modified (uncommitted)
- [core_utils.py](../core_utils.py) — modified (uncommitted)
- [prompts/PARSER_BUGS_HANDOFF_2026-05-02.md](PARSER_BUGS_HANDOFF_2026-05-02.md) — original triage
- [validation runs - json/AI Analyzed Json/KAY R RESOURCES (M) SDN BHD/KAY_R_RESOURCES_parser_quality_report.json](../validation%20runs%20-%20json/AI%20Analyzed%20Json/KAY%20R%20RESOURCES%20%28M%29%20SDN%20BHD/KAY_R_RESOURCES_parser_quality_report.json) — the grade-C report that triggered this work
- [scripts/recon_bug001.py](../scripts/recon_bug001.py) — cross-bank reconciliation script written this session (read-only)
- [scripts/validate_reference_statements.py](../scripts/validate_reference_statements.py) — 14-bank validator (run before any commit)
