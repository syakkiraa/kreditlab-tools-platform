# Track 1 Continuation Handoff

**Track 1 = optimizing the claude.ai web workflow** (the prompt + supporting files used by the analyst when uploading parser JSON to claude.ai for classification). Independent of Track 2 (`kredit_lab_classify.py` Python classifier) which is being built in a parallel session.

**Date of last handoff update:** 2026-04-29 (post-MUHAFIZ-acceptance-test)
**Last Track 1 work landed in:** `f86c991` (Phase 2 rule 3 — amount-divergence diagnostics). Acceptance-test result append uncommitted at handoff time.
**Phase 1 status:** ✅ COMPLETE. MUHAFIZ acceptance test PASSED 2026-04-29 — single-pass run, all expected outcomes verified, analyst confirmed turnaround improvement vs pre-template baseline.
**Phase 2 status:** ✅ COMPLETE. All 4 rules shipped. Rule 3 (amount-divergence) shipped as a diagnostics-only patch (always record `cr_total_gap`/`dr_total_gap`/`tx_count_gap`, require structured failure notes); thresholds unchanged per user direction. Verified live in MUHAFIZ run.

Read this file first when continuing Track 1 work in a new session.

---

## Repo state at handoff

| Item | State |
|---|---|
| Branch | `sprint-6/polish` |
| Local ahead of origin | 19 commits (1 Track 1 + ~18 Track 2) |
| Local behind origin | 0 |
| Track 1's last commit | `df206f4` (Phase 0: BUG-001 + v3.5.6 enum fix) |
| Track 2 latest known | `fbca8e6` (Sprint 7 #11/#12/#13 handoff append) |
| Push status | **NOT pushed.** Track 2 owns the push timing — they'll publish their WIP when ready, mine rides along. **Do NOT push without coordinating with the user.** |

---

## CRITICAL: Track 2 isolation rules

The parallel session is actively building `kredit_lab_classify.py`. Track 1 work must not interfere.

### 🟢 Files Track 1 OWNS (free to edit/create)

| Path | Purpose |
|---|---|
| `validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_*.md` | The system prompt for claude.ai web. Track 1's primary deliverable. |
| `prompts/CHANGELOG.md` | Track 1's prompt-version history |
| `prompts/TRACK_1_HANDOFF.md` | This file — update at end of each Track 1 session |
| `prompts/RUN_INPUT_TEMPLATE.md` | (To be created in Phase 1) |
| Any new `prompts/track1_*.md` files | Track 1 namespace |

### 🔴 Files Track 1 must NOT TOUCH

| Path | Why |
|---|---|
| `kredit_lab_classify.py` | Track 2 owns this entirely. Even reading it for context is fine; editing is not. |
| `prompts/NEXT_CHAT_PROMPT.md` | Track 2 appends handoffs here (commit `fbca8e6` is an example). Editing risks merge conflicts. |
| `prompts/CLASSIFIER_HANDOFF.md` | Track 2's brief; do not alter. |

### 🟡 Files SHARED — coordinate any change

| Path | Rule |
|---|---|
| `core_utils.py` | Additive changes only. No breaking refactors of public functions. If you add a new helper, document it. Track 2 imports from here. |
| `app.py`, per-bank parsers (`cimb.py`, etc.) | Track 1 should generally NOT modify. Only touch if you discover a specific parser bug that affects classification quality (like BUG-001). Always run the 14-bank validator before committing. |
| `validation runs - json/claude ai prompt file/CLASSIFICATION_RULES_v3_*.json` | Both tracks consume. Bumping version (e.g. v3.5 → v3.6) requires updating BOTH tracks' references. Coordinate via the user before bumping. |
| `validation runs - json/claude ai prompt file/BANK_ANALYSIS_SCHEMA_v6_3_*.json` | Same as rules — both tracks validate against it. Coordinate before bumping. |

---

## Phase 0 — COMPLETE ✅

Shipped in `df206f4`:

1. **S1: Parser BUG-001 fix** — `core_utils.stamp_statutory_buckets` now applies a side-gate:
   - Skips CR-side rows (statutory contributions are always outbound DR)
   - Skips rows where company's normalised name appears in description (own-party transfer earmarked for future statutory run)
   - Test case: MUHAFIZ Feb 2026 RM 600K CR `EPF PAYMENT MUHAFIZ SECURITY SDN` correctly returns `None` instead of wrong `KWSP`
   - 14-bank parser regression validator: PASS, no regressions

2. **A1: v3.5.6 enum fix** — `SYSTEM_PROMPT_v3_5_6.md` `ledger_cleaning_status` instruction now uses schema-compliant enum (`"CLEANED"` / `"VALIDATION_FAILED"` / `"SKIPPED"`) instead of the previous wrong values (`"PASSTHROUGH"` / `"PASSTHROUGH+RP_STAMPED"`).
   - Patched in place (same v3.5.6 label) so claude.ai project knowledge swap is a single-file replace
   - Patch noted in v3.5.6 changelog header + `prompts/CHANGELOG.md`

---

## Phase 1 — DELIVERABLE SHIPPED ✅ (acceptance test pending)

Shipped 2026-04-28 in this session (uncommitted at handoff time):

1. **`prompts/RUN_INPUT_TEMPLATE.md`** (new file) — structured pre-supply form. 5 sections: Company info, Confirmed RP1, Known factoring entities, Analyst decisions (commission cluster / gov-counterparty side / business model / account-type override), Special notes. Block delimited by `---BEGIN PRE-ANALYSIS INPUT---` / `---END PRE-ANALYSIS INPUT---`.
2. **`SYSTEM_PROMPT_v3_5_6.md` INPUT section** — now references the template as item 1; explicit instruction that when the block is present, the pre-analysis gate must NOT re-flag items it answers in `observations.concerns[]`. Patch noted in v3.5.6 changelog header (same v3.5.6 label retained — single-file project-knowledge swap).
3. **`prompts/CHANGELOG.md`** — Phase 1 entry added at top, before earlier Phase 0 entry.

**Acceptance test pending** (analyst-driven, not Claude-driven): re-run MUHAFIZ corpus with the filled template — expect single-pass classification with SHAUFIAH NUR ASHIKIN as RP4 and gov-CR routed to C26 instead of Unclassified. Record result in `prompts/CHANGELOG.md` under the Phase 1 entry once the test runs.

---

## Phase 1 — original spec (kept for reference)

**Goal:** Eliminate the v1→v2→v3 rerun pattern by pre-supplying analyst decisions BEFORE uploading parser JSON to claude.ai.

**Why this matters:** Per the 2026-04-22 MYTUTOR efficiency review, the dominant cause of slow runs is mid-run discovery (e.g. AI surfaces RP4 candidates after `build_top_parties` runs, triggering full re-classification). Pre-supplying everything kills that loop.

### Deliverable

Create `prompts/RUN_INPUT_TEMPLATE.md` — a markdown template with structured fields the analyst fills before each run. The completed template is pasted **above** the parser JSON when uploading to claude.ai.

### Required fields (minimum)

```markdown
# Pre-analysis input for THIS run

## Company information
- Company name (full legal): _______
- Statement period: _______
- Bank: _______

## Confirmed related parties (RP1)
List all directors, family members, sister companies, subsidiaries the analyst
already knows. AI uses this as confirmed RP1 — no MEDIUM-confidence guessing.

- (one per line, name + relationship)
- e.g. SHAHARUDDIN BIN SAMSI (Director)
- e.g. MUHAFIZ TECHNOLOGY SDN BHD (Sister Company)

## Known factoring entities (for C10)
- (e.g. PLANWORTH GLOBAL)

## Analyst decisions

### Commission cluster handling
- [ ] Treat as regular expense (independent contractors / agents)
- [ ] Treat as C05 salary (employees on payroll)

### Government counterparties (JANM, KERAJAAN, AKAUNTAN NEGARA, KASTAM)
- [ ] CR side: Trade revenue (operating income from government clients)
- [ ] CR side: Other (specify)
- [ ] DR side: Tax / customs duty payment

### Business model
- [ ] Standard SME (services / trading)
- [ ] Tuition academy / agency-based (commission-heavy)
- [ ] Security services (government clients common)
- [ ] Other: _______

## Special notes for the AI
(Free text — anything else the analyst wants the AI to know)
```

### Workflow change

Document in the template (and reference from v3.5.6 prompt):

1. Analyst opens `RUN_INPUT_TEMPLATE.md`, fills it for the current entity
2. In claude.ai web, pastes the filled template at the TOP of the message
3. Below the template, pastes / attaches the parser JSON
4. AI consumes template first → has all decisions upfront → no mid-run discovery

### Acceptance test

On the MUHAFIZ corpus:
1. Without template: previous run had unclassified RM 6.4M government revenue + missed SHAUFIAH NUR ASHIKIN as RP4
2. With template (pre-supply MUHAFIZ's RPs + analyst-decision "government CR = trade revenue"): both should resolve in a single run

### Estimated effort

- Template draft: 30 min
- One MUHAFIZ test run: ~10-15 min (depends on claude.ai throughput)
- Refinement based on first-run observations: 15-30 min
- Commit: 5 min

**Total: ~1-1.5 hours, single session.**

---

## Phase 2 — COMPLETE ✅ (all 4 rules shipped)

Rules 1, 2, 4 shipped 2026-04-28 in commit `3e3f0fc`:

1. **plate-as-RP-keyword exclusion (RP6)** — Malaysian plate regex `\b[A-Z]{1,3}\d{1,4}\b` now blocked from RP2/RP3/RP4/RP8 auto-detect scans. Added at the existing RP6 exclusion list in [SYSTEM_PROMPT_v3_5_6.md:171-173](validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md#L171).
2. **Government counterparty extension to C26** — Added new clause after the standard C26 test block. Gov-CR (KERAJAAN MALAYSIA / JANM / AKAUNTAN NEGARA / KASTAM / KEMENTERIAN/JABATAN/PERBADANAN/MAJLIS prefixes) now routes to C26. Pre-analysis template section 4b is the override channel. Government-DR unchanged.
3. **Rule 3 — amount-divergence — diagnostics-only patch** (shipped 2026-04-28, uncommitted at handoff time). User confirmed the existing rule structure is correct: ≤RM 1.00 = CLEANED, anything else = VALIDATION_FAILED, never modify the ledger to force balance. The fix was visibility, not thresholds:
   - **Always record the gap, even on PASS.** New `cleaning_stats` fields: `cr_total_gap` (signed, 2 dp), `dr_total_gap` (signed, 2 dp), `tx_count_gap` (signed int). Lets the analyst spot slow drift across runs before it crosses the failure line.
   - **Failure notes must be specific.** `observations.concerns` entry on `VALIDATION_FAILED` must name (a) failing side(s), (b) signed gap amount(s), (c) worst-contributing month, (d) worst-contributing counterparty. Vague `"delta = X"` notes no longer acceptable.
   - Edit at [SYSTEM_PROMPT_v3_5_6.md:692-705](validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md#L692-L705). Schema-permissive (no `additionalProperties: false` on `cleaning_stats`); no schema bump, no Track 2 coordination.
4. **IBG/DuitNow return pairing (C13 ↔ C16)** — New block added between C26/C27 section and Patronymic guard. Pairs outward DR + return CR within ±5 business days to same counterparty; DR→C13, CR→C16. ≥RM 1,000 pairs surface in `observations.concerns`; smaller pairs silent. Unpaired returns flag possible cross-period gap.

Patch notes added to v3.5.6 header + `prompts/CHANGELOG.md` for each rule.

**Note:** the prior version of this file referenced "lines 658-662" as the location of the amount-divergence rule. That was incorrect — those lines are the canonical 16 risk-signal flags table. The actual rule lives at [SYSTEM_PROMPT_v3_5_6.md:684-705](validation runs - json/claude ai prompt file/SYSTEM_PROMPT_v3_5_6.md#L684-L705) (counterparty-ledger totals validation).

---

## Phase 3-7 — queue (don't start without user check-in)

- **Phase 3:** Schema/rules updates (only if Phase 2/3 introduces new categories — currently none, so Phase 3 may be empty)
- **Phase 4:** Parser-side metadata enricher (`enrich_parser_output.py`) — biggest leverage piece
- **Phase 5:** Output validator (`validate_analysis.py`)
- **Phase 6:** Parser polish (deferred — non-urgent)
- **Phase 7:** Track 2 integration (when parallel session ships)

---

## First actions in the next Track 1 session

1. **Read this file first.** Don't act before reading it end-to-end.
2. **Verify state:**
   ```bash
   git branch --show-current     # expect: sprint-6/polish
   git log --oneline -5          # expect: df206f4 in there somewhere
   git status -sb | head -1      # expect: ahead of origin (count varies)
   git status --short            # expect: untracked-only or clean (unless Phase 1 commit still pending)
   ```
3. **Check whether Track 2 has shipped/pushed.** If origin has caught up with local (or moved past it), the parallel session pushed. Pull only if `git rev-list --count HEAD..origin/sprint-6/polish` > 0 AND user confirms.
4. **Check Phase 1 commit status.** If `prompts/RUN_INPUT_TEMPLATE.md` is still untracked or `prompts/CHANGELOG.md` / `SYSTEM_PROMPT_v3_5_6.md` still appear in `git status`, the Phase 1 commit hasn't landed — ask the user whether to commit before moving on. Do NOT auto-commit without explicit OK.
5. **MUHAFIZ acceptance test is COMPLETE** as of 2026-04-29 — see Phase 1 entry in `prompts/CHANGELOG.md` for the verified-outcomes list. No need to re-check unless the user wants a re-run on a different corpus.
6. **Confirm Phase 3+ is the next move with the user.** Phases 0-2 are now complete and acceptance-tested. Phase 3-7 queue is in this file below; per the original plan, do NOT start Phase 3+ without an explicit user check-in (they may re-prioritize, or new work may have surfaced from Track 2's progress).

---

## Hard rules for the next Track 1 session

1. **Never edit `kredit_lab_classify.py`.** Even if you think you're improving it. Track 2 owns it.
2. **Never edit `prompts/NEXT_CHAT_PROMPT.md`.** Track 2's handoff channel.
3. **Never push to remote without user explicit OK.** Especially since local is ~19 commits ahead with mixed Track 1 + Track 2 work.
4. **Never `git pull` without checking ahead/behind first.** If origin moved unexpectedly, surface to user before pulling.
5. **Never run `git reset --hard` or `git push --force`** under any circumstances on this branch.
6. **Run the 14-bank parser regression validator** (`python3 scripts/validate_reference_statements.py`) after any change to `core_utils.py` or per-bank parser files. Report PASS/FAIL before committing.
7. **Surface unexpected branch state.** If the branch isn't `sprint-6/polish`, or if local has uncommitted modifications you didn't make, STOP and tell the user before doing anything else.

---

## Quick context for fresh Claude session

- **Project:** Bank statement analysis pipeline for Kredit Lab. Parser → AI classifier → HTML report.
- **You are working on Track 1:** the AI prompt that runs in claude.ai web. Production workflow. User-facing.
- **Track 2 is in parallel:** building `kredit_lab_classify.py` to eventually replace the AI-driven classification with deterministic Python. Don't interfere.
- **User's name:** Luqman. Credit analyst building the system. Tired but engaged. Prefers concrete actions over discussion.
- **User preferences (from memory):** terse responses, no rail-label jargon, verify before asserting, inspect data first, cross-bank-safe rules only, no silent commits.
- **Recent context:** Sprint 6 wrapped 2026-04-27. Sprint 7 in progress. Phase 0 of the optimization plan shipped 2026-04-28 in `df206f4`.
