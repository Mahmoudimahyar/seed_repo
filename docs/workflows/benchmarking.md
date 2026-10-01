# Execution-method benchmarking

Select the least expensive sufficient METHOD, not only an LLM: remove unnecessary work,
reuse existing code/standard APIs, test parsers and specialized models, then small/strong
LLMs, bounded agents and human review as needed. An API is not automatically correct;
JSON validity proves shape, not factual accuracy or recall.

## Runnable no-credential demonstration
The included email fixtures are synthetic and derived from a known rule. They demonstrate
pipeline mechanics only; they are not a real NER benchmark or evidence of model quality.

```bash
python3 scripts/run_candidate.py --cases evals/demo/cases.jsonl --candidate evals/demo/baseline-candidate.json --out .seed-local/evals/baseline.json
python3 scripts/seed_eval.py score --cases evals/demo/cases.jsonl --predictions .seed-local/evals/baseline.json --config evals/demo/baseline-score.json --out .seed-local/evals/baseline-report.json
python3 scripts/run_candidate.py --cases evals/demo/cases.jsonl --candidate evals/demo/empty-candidate.json --out .seed-local/evals/empty.json
python3 scripts/seed_eval.py score --cases evals/demo/cases.jsonl --predictions .seed-local/evals/empty.json --config evals/demo/empty-score.json --out .seed-local/evals/empty-report.json
python3 scripts/seed_eval.py compare --incumbent .seed-local/evals/baseline-report.json --candidate .seed-local/evals/empty-report.json --policy evals/demo/promotion-policy.json --out .seed-local/evals/comparison.json
```

The final command intentionally exits 1 with REJECT. Demo data cannot authorize promotion.
Evidence outputs refuse overwrite. Use a new run directory when repeating experiments.
A score command finishing successfully means scoring executed, NOT that the model passed
requirements. Inspect accuracy/coverage/errors and the separate comparison decision.

## Real task families
Define input distribution, output schema, verified references, acceptable risk, coverage,
latency, privacy and lifecycle cost. Keep development, regression, challenge, production
sample and protected release sets distinct; split by source/customer/document/template
where needed. The loader rejects a group spanning splits in the supplied dataset, but
cannot detect hidden duplicate content in outside datasets. Protect release datasets from
prompt tuning and skill improvement; repeated selection needs fresh held-out evaluation.

Saved predictions from any model or specialized extractor can be scored. `run_candidate.py`
supports trusted external argv adapters after `--allow-external`; each gets {id,input}
without labels and returns a validated prediction/abstention/error response described below. Use official provider SDKs, stable model
versions, exact prompt/config hashes and provider cost records in the adapter. No provider
credentials or universal API adapter are bundled. External adapters are NOT sandboxed;
review code, bound network access/resources and check provider terms before execution.
Monetary costs are adapter-reported; unknown costs stay unknown, not zero. CPU/idle costs,
labeling, reruns, escalation and maintenance need separate accounting.

## What the executable scorer does
Exact JSON and entity span/type checks; invalid and missing outputs; abstentions; record
accuracy; entity precision/recall/F1; coverage; slices; latency and cost; paired regressions;
Wilson 95% intervals for binary record success. Intervals assume representative independent
cases, not clustered production data. The simple promotion screen is deliberately
conservative, not a formal equivalence, non-inferiority or counterfactual proof.

`consensus` groups model labels but ALWAYS marks them provisional. Review disagreements
and audit a representative sample of agreements, including all-negative cases. Shared
errors and judge biases remain possible. Label provenance is declared by the dataset owner,
not authenticated by this tool. Use independent human adjudication/provenance where needed.
Prediction-powered inference and conformal methods are research options, not implemented
statistical guarantees. Extend through an established evaluation package when appropriate.

## Promotion lifecycle
Discover → license/privacy/compatibility filter → smoke test → task-specific evaluation →
review → replay/shadow → canary → approved configuration update → monitoring/rollback.
Our comparator only produces REJECT or ELIGIBLE_FOR_REVIEW and never changes production.
Automated low-risk promotion requires a separately approved trusted release policy; new
privacy recipients, safety rules, protected evaluators and consequential actions stay gated.
Version aliases, SDKs, tools, prompts, schemas, preprocessing and data shifts can all trigger
reevaluation. A price-only change may only need cost recomputation. Scheduled runs need an
explicit budget, supported providers and protected secrets; no paid cron is enabled by default.

## Versioned result handoff (0.3.1)

`run_candidate.py` writes one `seed-prediction-run` envelope, not a prediction file plus an
ignored sidecar. It includes dataset fingerprint, exact generating candidate/configuration,
executor fingerprint, run ID, timestamps, prediction digest and manifest digest. The scorer
checks those bindings and refuses candidate/config/dataset relabeling or changed results.
Hashes detect inconsistency; anyone controlling all fields can recompute them. They are not
provider signatures or independent attestation. Keep secrets out of persisted candidate configs.

Each adapter response may supply `status: PREDICTED | ABSTAINED | ERROR`, `prediction`,
`abstained`, `error_code`, and `cost_usd`. IDs and elapsed latency belong to the runner. Unknown
fields, conflicting statuses, nonfinite values and an abstention hiding a prediction are rejected.
An error/abstention is not covered; unknown costs stay unknown. A protocol/timeout/output-limit
failure is saved as an ERROR row and stops later cases; it never becomes an empty correct answer.
The child receives only ID/input, not expected labels. Output is bounded while it is produced,
and POSIX descendants are cleaned up by the shared process supervisor.

Legacy raw lists can still be scored for exploration, labeled `UNBOUND_LEGACY`. Neither an
incumbent nor a candidate with unbound provenance can be eligible for review. Regenerate a run
from actual source/configuration rather than fabricate metadata for old predictions.

Comparison policy is validated against `schemas/promotion-policy.schema.json`; unsupported
constraints and missing required keys fail closed. `min_coverage` is required and enforced alongside
quality, slices, paired regressions, latency and cost. Bounds/counts are type-checked. This remains
screening for review, not a formal noninferiority test or automatic deployment permission.
