---
name: seed-evaluate
description: Design or compare a recurring predictive task, model configuration, retrieval policy, or skill change using task-specific evidence. Not a reason to benchmark every prompt.
---

# Evaluate predictive work and skill changes

## Define
Follow docs/workflows/evaluation.md. Register the task contract and required quality,
coverage, critical-error, cost, privacy and latency constraints. Compare deterministic,
specialized and LLM methods where suitable. Existing external benchmarks shortlist;
the actual workload decides. No hard-coded model winner or guaranteed accuracy.

## Measure
Select a maintained harness instead of reinventing one. Separate development, protected
release, regression and representative recent data. Model agreement yields provisional
labels; audit agreements and disagreements and preserve provenance. Score appropriate
behavior, error groups, abstention, total cost and uncertainty. Evaluate the entire model/
prompt/tool/retry configuration and downstream workflow. Do not leak evaluation answers
or weaken scorers to make a candidate win.

## Promote carefully
Propose reviewed changes, safe shadow/canary tests, monitoring and rollback. Do not duplicate
real side effects in shadow tests. Protect evaluator/safety policy from self-editing by
the candidate-generating agent. A skill lesson becomes a proposed diff, not automatically
an active rule; compare old/new on held-out cases before approval.

## Included execution tools
Use docs/workflows/benchmarking.md for seed_eval.py and the trusted-candidate interface.
The synthetic demo validates mechanics, not model quality. Consensus stays provisional,
unknown cost stays unknown, and comparison yields a review proposal, never auto-deployment.
For complex grading, reuse a maintained domain harness rather than extending a tiny scorer
into an unvalidated universal evaluation framework.

## Integration contract

Use the versioned candidate-run envelope so abstention/error status and provenance survive adapter→scorer→comparator. Raw legacy arrays are exploratory only. min_coverage is enforced; unknown policy fields are errors, not ignored preferences. Do not relabel a run or fabricate metadata for old outputs.
