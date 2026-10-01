# Task/model evaluation and skill improvement

This is a policy and contract template, not a shipped benchmark service or model router.
Register recurring predictive task families, not every prompt. Define inputs, supported
distribution, schema, annotation policy, critical error types, quality/coverage, latency,
privacy, cost requirements, and abstention/escalation behavior.

Compare deterministic baselines, specialized predictors, inexpensive LLMs, and stronger
models where suitable. Evaluate the full configuration: revision, prompt, tools, decoding,
preprocessing, retry/escalation policy, and runtime. Optimize total cost per accepted outcome,
including validation, retries, research, labeling, human correction, and operations.

Use verified references for release evaluation. Model consensus creates provisional
labels, not truth. Audit representative agreements as well as disagreements and high-risk
cases. Preserve label provenance, adjudication rules, source spans when appropriate, and
uncertainty. Human labels also need quality control. Keep development, held-out release,
regression, and representative recent-production sets distinct; avoid related-data leakage.

Report task-appropriate scores, important input groups, coverage/abstention, critical errors,
cost, latency, and uncertainty. A public benchmark can shortlist candidates, but the target
workload decides acceptance. JSON validity is not factual or extraction-completeness proof.
No candidate is "perfect" because it passed a finite sample.

Automate candidate tests only after a usable evaluation exists. Propose promotion through
review, safe shadow evaluation, canary, monitoring, and rollback. Do not duplicate real
side-effecting actions during shadow tests. Auto-promotion is a separately approved
low-risk policy, not the default. Protect evaluators, held-out data, and release rules
from unilateral changes by the candidate-generating agent.

For learned skills: capture a reusable lesson, propose a small change, compare old/new
versions on development and held-out tasks, approve/version, and monitor. Project-specific
workarounds stay in project memory. Installing Hermes/Superpowers/etc. is not required.

Use a maintained harness such as Inspect AI or Promptfoo when a real evaluation workload
is ready; select one based on requirements rather than installing both automatically.
See the example contract under `evals/`. No external evaluation has been run for this release.
