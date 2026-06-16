# Track 2 handoff — picking up after session 15

State at end-of-session-15 (2026-05-13). Use this when starting a fresh
chat to continue Track 2 work.

## Current state

**Branch:** `track-2-development` at commit `4c8f4e5`. One Track 2
commit in session 15 since the previous handoff (`38db16d`).

**Test count:** 745 / 745 (was 719 at session 14 end; +26 across one
commit, all session 15). Run `python -m unittest discover tests` to
verify.

**One Track 2 commit added since the s15 handoff:**

| Commit | Function(s) / file | Tests | Role |
|---|---|---|---|
| `4c8f4e5` | `build_track2_result`; `_build_monthly_for_account`; `_build_consolidated_track2`; `_build_accounts_track2`; `_build_top_parties_track2`; `_build_parsing_metadata_track2`; `_build_unclassified_track2`; `_summary_for_flags_track2`; `_sanitize_statutory_compliance_for_schema`; `_sanitize_pdf_integrity_for_schema`; `_monthly_breakdown_for_cp`; `_aggregate_classified_into_monthly`; `_empty_monthly_entry`; `_round_monthly_entry`; `_coerce_account_no`; `_CATEGORY_TO_MONTHLY_BUCKET`; `_OVERALL_STATUS_SCHEMA_MAP`; `_TRACK2_PDF_LAYER_*`; `_TRACK2_SCHEMA_VERSION`; `_TRACK2_RULES_VERSION`; `_TRACK2_*_THRESHOLD` | 26 | Per-row dispatcher Slice C Part 1 — v6.3.5 result orchestrator (s15) |

All new code lives in
[kredit_lab_classify_track2.py](../kredit_lab_classify_track2.py); new
tests in `tests/test_track2_orchestrator.py` (9 new classes).

## What session 15 unblocked

**The Track 2 pipeline can now produce a full v6.3.5-schema result dict
end-to-end.** `build_track2_result(transactions, ...)` is the public
surface side-by-side validation will consume.

**Validated against the corpus (5 files, all PASS schema validation):**

| File | tx | months | accts | flags fired | top_payers | unclassified listed |
|---|---|---|---|---|---|---|
| Maybank Zaim | 2688 | 12 | 2 | 7/16 | 10 | 137 |
| Maybank Hydrise | 1013 | 6 | 1 | 3/16 | 10 | 194 |
| MBB Shahnaz Builders | 181 | 4 | 1 | 7/16 | 10 | 35 |
| Juta UOB | 682 | 6 | 1 | 8/16 | 10 | 215 |
| Upell UOB | 264 | 6 | 1 | 3/16 | 10 | 56 |

**Part 1 wires (cleanly from existing helpers):**

```
report_info ............ derived from transactions
accounts ............... per-account aggregation; account_type_determination
                         defaults to LOW confidence (parser meta not threaded)
monthly_analysis ....... per-(account, month) entries, all 58 required keys
                         populated; FX / round-figure / high-value overlays
                         from compute_* helpers; reconciliation status from
                         balance trail (CR or OD)
consolidated ........... rolled up from monthly + statutory_compliance
top_parties ............ top 10 payers/payees from ledger with monthly_breakdown,
                         synthetic labels filtered, related-party flag honored
flags.indicators ....... 16-item array via compute_risk_flags
parsing_metadata ....... per-account-month reconciliation slots
large_credits .......... from compute_large_credits (RM 100K+)
unclassified_transactions .. RM 10K+ listing
classification_config .. Track 2 metadata snapshot
pdf_integrity .......... sanitised pass-through (layer-enum coerce, null
                         detail drop, severity counts auto-derived)
counterparty_ledger .... pass-through
```

**Part 1 stubs (filled in Part 2 after RP foundation):**

```
own_related_transactions.summary ... uses consolidated own/related totals
                                     (all zero until C01-C04 fire)
own_related_transactions.transactions .. empty
loan_transactions.disbursements/repayments .. empty
observations.positive/concerns ..... empty arrays
```

## Critical findings / decisions from session 15

### Two sanitisers required for schema compliance

The Track 2 result mostly satisfies the v6.3.5 schema as-is, but two
surfaces required mapping:

1. **`statutory_compliance.overall_status`** — Track 2's s12 calibration
   introduced two extra verdicts (`SUB_THRESHOLD`, `CHANNEL_BLIND`) that
   are not in the schema enum `[COMPLIANT, GAPS_DETECTED, CRITICAL]`.
   `_sanitize_statutory_compliance_for_schema` projects them:
   - `SUB_THRESHOLD` → `COMPLIANT` (employer doesn't have an obligation)
   - `CHANNEL_BLIND` → `GAPS_DETECTED` (compliance not fully verifiable)

   The original Track 2 verdict survives on the
   `subthreshold_employer.is_subthreshold` and
   `channel_blind_employer.is_channel_blind` extension fields (allowed by
   `additionalProperties`). The downstream HTML renderer reads those for
   the rich view.

2. **`pdf_integrity`** — parser-emitted layer values include the
   3-layer-outside-the-schema-enum set (`text_layers`, `metadata`,
   `cross_validation`). They get mapped onto `'structural'`.
   Non-dict `detail` fields are dropped. Per-file severity counts
   (`finding_count` / `high_count` / `medium_count` / `low_count`) are
   auto-derived from `findings` when absent.

   This mirrors Track 1's `_sanitize_pdf_integrity` behaviour. Track 2
   does NOT import Track 1; the sanitiser is re-implemented.

### Schema-version mismatch caught

`report_info.schema_version` is a JSON Schema `const = "6.3.5"`, NOT
`"v6.3.5"`. The orchestrator emits the const-correct value. **If the
schema bumps to 6.3.6+** the `_TRACK2_SCHEMA_VERSION` constant needs to
update with the rest of Track 2.

### Top-parties `monthly_breakdown` derived from ledger transactions

Each top_payer / top_payee entry needs a `monthly_breakdown` array per
the schema's `$defs/party`. The orchestrator walks each counterparty's
ledger transactions, groups by `YYYY-MM`, and emits
`{month, amount, count}` per month. Synthetic-label filtering reuses
`_is_synthetic_counterparty_label` from s14.

### Single-pass classification, multi-pass per-account aggregation

`build_track2_result` calls `classify_transactions` ONCE over the full
input. Then it groups by `account_no` and runs `compute_monthly_aggregates`
per account (mandatory — `compute_monthly_aggregates` and
`compute_monthly_eod` precondition single-account input). Per-row
classifications are sliced by account_no using `zip(transactions,
classified)`. This works because `classify_transactions` preserves
input order (s13 invariant).

Rows without an `account_no` field bucket under the placeholder string
`"_unknown"` — same convention as the parser monthly summary builders.
This keeps the orchestrator stable on older parser outputs.

### C24 bank fees intentionally NOT in monthly_analysis

The v6.3.5 monthly schema has no per-month bank-fees field. Bank-fee
classifications still happen (C24 rung fires); the amounts contribute
to `gross_debits` but are not bucketed separately. They surface through
the C24 flag indicator instead. This is a deliberate Track 1 / Track 2
shared decision.

### Monthly net_totals use compute_net_totals (s7)

The s7 net-totals helper has a specific subtraction formula:
- `net_credits = gross_credits - own_party_cr - related_party_cr -
  loan_disbursement_cr - fd_interest_cr - reversal_cr - inward_return_cr`
- `net_debits = gross_debits - own_party_dr - related_party_dr -
  loan_repayment_dr`

The orchestrator calls `compute_net_totals(...)` per month after
aggregation. The result is per
`project_track_2_schema_divergence.md` memory: C12 / C16 ARE excluded
from net_credits and C04 / C11 ARE excluded from net_debits, matching
v6.3.5 spec literally. Track 1 has the inverse (C12/C16 included).
**Side-by-side validation will flag this delta intentionally.**

### `compute_risk_flags` summary glue

`_summary_for_flags_track2` projects the consolidated dict into the
shape `compute_risk_flags` expects (s2 signature predates the orchestrator
by 13 sessions). Some counts not present in `consolidated`
(returned-cheque counts, cash-deposit count, round-figure count,
high-value count) are derived from the classified row stream on
the fly. Cleanest place to keep them.

### Reconciliation tolerance is RM 1.00, sign-flipped for OD

Per-month `reconciliation_status` is `PASS` when
`|opening + gross_credits - gross_debits - closing| <= 1.00` for CR
accounts; for OD (when `account_meta` says so) the formula is sign-
flipped (`opening + gross_debits - gross_credits`) matching the
Alliance / SAP-i convention. Outside tolerance, `reconciliation_status
= FAIL` and `data_quality_note` carries a human-readable summary.

## Sync state vs main

Still 17 commits behind main (same as end-of-s14). The `app.py`
conflict is unchanged. Defer the merge pending a dedicated sync
session.

## Cumulative state across sessions 1-15

**Functions ported / built (53 total):**

- s1-s14 — see previous handoff for complete list (38 functions).
- **NEW in s15:** `build_track2_result` (public entry point) +
  15 private helpers + 10 module-level constants:
  - `_build_monthly_for_account`, `_aggregate_classified_into_monthly`,
    `_empty_monthly_entry`, `_round_monthly_entry`,
    `_build_consolidated_track2`, `_build_accounts_track2`,
    `_build_top_parties_track2`, `_monthly_breakdown_for_cp`,
    `_build_parsing_metadata_track2`, `_build_unclassified_track2`,
    `_summary_for_flags_track2`,
    `_sanitize_statutory_compliance_for_schema`,
    `_sanitize_pdf_integrity_for_schema`, `_coerce_account_no`.
  - `_CATEGORY_TO_MONTHLY_BUCKET`, `_OVERALL_STATUS_SCHEMA_MAP`,
    `_TRACK2_PDF_LAYER_VALID`, `_TRACK2_PDF_LAYER_MAP`,
    `_TRACK2_SCHEMA_VERSION`, `_TRACK2_RULES_VERSION`,
    `_TRACK2_CLASSIFIER_VERSION`, `_TRACK2_EXECUTION_MODE`,
    `_TRACK2_LARGE_CREDIT_THRESHOLD`,
    `_TRACK2_UNCLASSIFIED_LISTING_THRESHOLD`,
    `_TRACK2_ACCOUNT_NO_FALLBACK`.

## Mid-flight state — DO NOT TOUCH

Same as previous handoffs. Working tree carries uncommitted
modifications and untracked items from **other workstreams**. Rule
unchanged: stage Track 2 work explicitly by path.

## Big-picture progress

15 sessions in. Previous estimate at end-of-s14 was 6-10 remaining;
with Slice C Part 1 in, **5-9 remaining** to MVP.

**Remaining to MVP Track 2 (passes side-by-side on 6 corpora):**

| Slice | Sessions | Gates |
|---|---|---|
| Slice C Part 2 (observations + own_related_transactions list + loan_transactions list) | 1 | Mostly composition; can ship before RP if needed |
| RP foundation sprint (RP3 scanner + RP6 constants, then RP2/5/7/8) | 2-3 | Unblocks C01-C04, C10, C11, factoring, M7 |
| Tier 3 remainder (C10 known-factoring, C11 priority logic, C11 account-number-only) | 1 | After RP foundation |
| `SYSTEM_PROMPT_TRACK2_v0_1.md` draft (Tier 4 prompt) | 1 | After dispatcher + RP |
| Side-by-side validation gate + corpus runs | 1-2 | After prompt |
| Bug-fix iteration on validation findings | 1-2 | After validation |

**Realistic remaining: 5-9 sessions to MVP.**

## Open items the user can tackle next

### Option 1 — Slice C Part 2 (Recommended; small, finishes orchestrator)

Wire the three sections currently stubbed:

- `observations.positive` / `observations.concerns` — derive 4-8
  human-readable strings each from the flags + consolidated. v6.3.4
  raised the cap from 5 to 8.
- `own_related_transactions.transactions[]` — list rows whose
  classification is C01/C02/C03/C04 (today: empty since the rungs are
  blocked; the listing builder itself is what's needed).
- `loan_transactions.disbursements[]` / `loan_transactions.repayments[]`
  — list rows classified as C10 / C11.

Roughly 1 session. Lights up immediately when RP foundation lands.

### Option 2 — RP foundation sprint (Highest leverage; bigger commitment)

Rebuild RP3 scanner + RP6 constants in Track 2 independently of Track 1.
Then build RP2/5/7/8 from v3.5.6 prompt spec.

2-3 sessions for the foundation alone. Unlocks five categories (C01,
C02, C03, C04, C10, C11) and the corresponding monthly_analysis buckets
already in place from s15.

### Option 3 — Side-by-side validation harness

Build a small CLI / script that runs `build_track2_result` AND Track 1's
`analyze_bank_statement` on the same corpus file and emits a structured
diff (which keys / counts / amounts differ, and by how much). This is
the gate for "MVP" — once Track 2 is within tolerance of Track 1 on the
6-corpus baseline, it ships.

Roughly 1 session. Can ship before RP foundation since the differences
will be informative (Track 1 has C01/C03 fires, Track 2 has zero — that's
expected and tells the analyst what's left).

### Smaller alternative — MYTUTOR-shape business-model signal

Same as previous handoffs — unchanged in scope.

### Blocked items (unchanged from s14)

Same as previous: C01/C02 own-party, C03/C04 RP, C10/C11 deterministic,
CIMB AI_ASSIST.

## First commands the next session should run

```bash
git status --short                              # confirm known-dirty
git branch --show-current                       # MUST be track-2-development
git log --oneline 38db16d..HEAD                 # s15 handoff endpoint to now
python -m unittest discover tests 2>&1 | tail -5  # confirm 745 / 745
```

Expected output of the last command:
```
Ran 745 tests in 0.0XXs
OK
```

The `git log` should show:

```
4c8f4e5 Track 2 session 15: dispatcher Slice C Part 1 — v6.3.5 result orchestrator
38db16d prompts: Track 2 session-15 handoff (after session 14)
```

If any of these don't match, **stop and investigate** — don't write
Track 2 code on a drifted branch.

## Branch-stability guard

No new occurrences in s15. Seventh recurrence was s13. Durable
mitigation:
`git worktree add ../Bank-Statement-Track2 track-2-development`
(creates a sibling physical checkout dedicated to Track 2). User has
declined seven times now — only offer again if it bites harder.

## Architecture rules (re-read before any code)

Unchanged from previous handoff. The s15 orchestrator follows them all:

- Track 1 files frozen indefinitely.
- Track 2 must NOT import from Track 1 (`kredit_lab_classify.py`).
  Slice C re-implements `_sanitize_pdf_integrity`, `_ledger_key`,
  `build_monthly_analysis`, `build_consolidated`, etc. from scratch
  rather than importing.
- Parsers and `core_utils` are SHARED infrastructure.
- `build_counterparty_ledger` lives in `app.py` — Track 2 consumes its
  output as a kwarg, never imports it.
- All Track 2 code lives in `kredit_lab_classify_track2.py`. New tests
  in `tests/test_track2_*.py`.

**Deliberate v3.5 divergences locked through s15:**

- `COMMISSION_BLOCK_RE` (s11).
- `OWN_ACCOUNT_BLOCK_RE` (s12).
- `SUBTHRESHOLD_TOTAL_SALARY_RM` / `CHANNEL_BLIND_*` thresholds (s12).
- Dispatcher priority follows v3.5 `classification_order` LITERALLY
  (s13).
- Synthetic-label filter mirrors `app.py`'s `_OWN_PARTY_PROTECTED_LABELS`
  (s14).
- **NEW in s15:** `_OVERALL_STATUS_SCHEMA_MAP` projects the Track 2
  SUB_THRESHOLD / CHANNEL_BLIND overall_status verdicts onto the
  schema-valid `[COMPLIANT, GAPS_DETECTED, CRITICAL]` enum at
  serialisation time. The original verdict survives on the
  subthreshold_employer / channel_blind_employer extension fields.

## Out of scope for the next session

Unchanged from previous handoff:

- Don't edit Track 1 files.
- Don't run `git add -A` / `git add .` / `git stash`.
- Don't initiate parser or `core_utils` edits without explicit user
  approval.
- Don't attempt the main → track-2-development merge unless explicitly
  scoped as a sync session.
- Don't push to origin without explicit user approval. **Twelve Track 2
  commits** + five handoffs sitting local since 2026-05-11.

## Memory entries that should already be loaded

Unchanged from previous handoff. No new memory entries needed — the
s15 work is fully documented in this handoff + the orchestrator
docstrings.

If any seem stale, refresh from the actual code — memory records are
point-in-time snapshots and the truth is in the repo.

## Suggested first action for the next session

Pick from:

1. **Slice C Part 2** — 1 session, finishes the orchestrator with the
   three sections currently stubbed (observations + own_related list +
   loan list). Self-contained.
2. **Side-by-side validation harness** — 1 session. Highest "is the
   orchestrator actually right?" leverage. Builds a CLI/script that
   diffs Track 2 vs Track 1 output on the corpus, surfacing which keys
   / counts / amounts differ.
3. **RP foundation sprint** — 2-3 sessions. Highest downstream leverage.
   Lights up C01-C04 / C10-C11 / M7 stamping.

Option 1 finishes the orchestrator scaffold cleanly. Option 2 is the
gate-to-MVP item — it's what actually tells us whether Track 2 is ready
to consider sellable, and unlike Option 3 it doesn't depend on more
classifier work first. The user's s8-s13 pattern of "low-risk-and-
unblocked-first" points at Option 1 followed by Option 2 in the next
two sessions.
