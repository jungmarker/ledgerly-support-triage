# Design notes

## Decision and contract

Can suggested ticket routing improve on noisy manual categories while exposing uncertainty?

Ticket text → TF-IDF/logistic baseline trained on noisy agent categories → validation threshold → later unseen-account evaluation → human review or advisory routing.

The input contract is the Ledgerly raw CSV/schema documented in the pinned source repository. Monetary values are USD, dates refer to the synthetic company calendar and the snapshot is September 30, 2026. Reads are local and source files are never modified. Missing or malformed required columns fail visibly rather than silently inventing input fields.

## Evaluation

Training uses pre-2026 tickets from 60% of accounts. Validation uses January–March tickets from another 20%; test uses April–September tickets from the final 20%. Validation chooses a threshold targeting 95% category accuracy with at least 20 samples. Cancellation always requires review.

Category accuracy/macro-F1, confusion matrix, review coverage, accuracy on accepted suggestions and separate novel-wording stress results.

The tests use small constructed examples to catch cutoff leakage, incorrect identity decisions, review bypasses or revenue reconciliation errors. They do not merely assert that the pipeline runs. The full seeded pipeline runs in CI to expose schema and integration failures.

## Operator workflow

Run the analysis, read metrics.json, inspect detailed CSV exceptions or predictions, and review the narrative before taking a business action. Reruns replace the reports in the selected output folder. Save previous output folders if you need historical runs. Data is regenerated from the pinned source; no credentials are required for local analysis.

## Production changes

Use source contracts and historical snapshots, least-privilege storage, access controls, execution logging, retry/idempotency policies and data freshness monitoring. Separate feature generation from labeled evaluation and version both data and model configuration. Validate on representative real data before setting business thresholds. This demo uses local files and full rebuilds at about a few thousand accounts; it is not a benchmark of distributed scale.

## Known limitations

This is a local ML baseline, not an LLM or autonomous agent. Synthetic templates can inflate results even across accounts and time. Priority and subtle churn signals are not reliably recoverable from generated text and require human review. Suggested route names are illustrative; model confidence is not a correctness guarantee. No helpdesk API writes.

## Interview walkthrough

1. Explain the business question and the input table grain.
2. Reproduce the report and trace one result to its source rows.
3. Explain the baseline, failure cases and why the evaluation split is appropriate.
4. Show the adversarial unit test and make a small behavior change.
5. Describe the changes needed for reliable operation on real company data.
