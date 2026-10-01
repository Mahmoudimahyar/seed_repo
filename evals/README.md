# Evaluation tools and task contracts

This distribution DOES include runnable tools: `scripts/run_candidate.py`, `scripts/seed_eval.py`,
exact JSON/entity scorers, a trusted external-command adapter, provisional consensus grouping,
and a strict review-eligibility comparator. The synthetic demo in `evals/demo` exercises their
interfaces without paid credentials. It is not a verified benchmark of real models.

Use [benchmarking](../docs/workflows/benchmarking.md) for executable commands and the versioned
prediction-run protocol. Use [evaluation policy](../docs/workflows/evaluation.md) for designing
real tasks and protecting release data. `tasks/example-extraction` is a contract template;
`wayfinding` contains unexecuted agent-comparison scenarios, not a completed client benchmark.

Abstention, execution error, valid prediction, unknown cost, and missing output are distinct.
Unknown comparison constraints are rejected. Raw legacy prediction lists can be explored but
cannot establish promotion eligibility. Saved runner output binds dataset and configuration
through local hashes, not authenticated provider attestation.

There is no paid benchmark schedule, real labeled corpus, hosted labeling service, automatic
model/skill promotion, or claim that consensus is ground truth. Reuse a maintained domain
harness for requirements beyond the bundled small scorers.
