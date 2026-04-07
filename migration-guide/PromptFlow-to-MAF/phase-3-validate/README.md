# Phase 3 — Validate Output Parity

Run your captured PF outputs and the new MAF workflow against the same test inputs, then score semantic similarity using the Azure AI Evaluation SDK.
Similarity scores are 1–5 (5 = most similar).

## Setup

1. Capture 20–30 real queries from your PF app and save them as a CSV with columns `question` and `pf_output`. See [test_inputs.csv](test_inputs.csv.md).

2. In [parity_check.py](parity_check.py), update the workflow import at the top of the file to point at your module.

## Run

    cd phase-3-validate
    python parity_check.py

Outputs `parity_results.csv`. Rows below the threshold are printed to stdout.

## Interpreting scores

| Score | Meaning |
|---|---|
| < 3.5 | Outputs diverge --> check for missing prompt context or unmigrated nodes |
| 3.5 – 4.5 | Minor phrasing differences --> generally acceptable |
| > 4.5 | Strong semantic match --> safe to proceed to Phase 4 |

Do not proceed to Phase 4 until mean similarity is consistently ≥ 3.5.
