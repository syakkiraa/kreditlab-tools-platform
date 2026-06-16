# Track 1 verify-harness regression suite

Golden-snapshot regression tests for the 6 verify corpora. Guards
parser + classifier + counterparty-ledger + reconciliation output
against accidental shared-infrastructure regressions.

## Why

Track 1 is frozen, but its inputs aren't. Parsers (`maybank.py`,
`cimb.py`, etc.) and shared helpers (`core_utils.py`, `app.py`
utilities, `kredit_lab_classify.py` rulebook) are still being edited
to fix Track 2 bugs. This suite catches when a "Track 2 only" fix
silently changes Track 1's classification rate or counterparty
extraction on the 6 reference corpora.

## Coverage

| Snapshot | Bank | Corpus | Notes |
|---|---|---|---|
| `mazaa_pbb` | Public Bank | `Bank-Statement/PublicBank/3/*.pdf` | Tuition profile, ~92% rate |
| `felcra_rakyat` | Bank Rakyat | `Bank-Statement/BankRakyat/8/*.pdf` | Contracting profile, ~59% rate |
| `waja_rhb` | RHB | `Bank-Statement/RHB/8/*.pdf` | ~27% rate |
| `bimb_kmz` | Bank Islam | `Bank-Statement/BankIslam/6/*.pdf` | ~40% rate |
| `bimb_mytutor` | Bank Islam | `Bank-Statement/BankIslam/Mytutor Academy/*.pdf` | Password-protected; ~1% rate |
| `bimb_principal_gas` | Bank Islam | `Bank-Statement/BankIslam/5/*.pdf` | ~31% rate |

The rate spread (1% to 92%) is the rate-variance lever the ship-ready
strategy memo flags. These snapshots are the baseline lifts have to
beat.

## Run

```bash
# Default fast-test run (regression auto-skipped, ~0.1s):
python -m unittest discover tests

# Opt-in regression run (parses ~35 PDFs, ~75s):
RUN_REGRESSION=1 python -m unittest tests.regression.test_snapshots -v
```

## Regenerate after an intentional behavioural change

```bash
python scripts/regenerate_regression_snapshots.py           # all 6
python scripts/regenerate_regression_snapshots.py mazaa_pbb # one
```

Commit the refreshed snapshot JSONs in the **same** commit as the code
change so the diff is reviewable.

## Adding a new corpus

1. Append a dict to `CORPORA` in `_harness.py` with: `label`,
   `glob_pattern`, `parser_key` (must be one of `pbb`/`bimb`/`rakyat`/`rhb`,
   or extend `_parse_one` for a new parser), `bank_name`, optional
   `password`.
2. Run `python scripts/regenerate_regression_snapshots.py <label>` to
   produce the golden file.
3. Commit `_harness.py` + the new `snapshots/<label>.json` together.

The test discovery in `test_snapshots.py` is dynamic, so the new
corpus picks up a test method automatically.
