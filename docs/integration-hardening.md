# Integration hardening — 0.3.1-rc.1

This is a correction release for the audit of 0.3.0-rc.1, not another prompt bundle.
It separates retrieval, execution integrity and export policies; connects already-declared
contracts to consumers; and makes applicability and verification status explicit.
Read [validation](validation.md) for actual observed results. A test's existence is not a pass.

## Finding-by-finding disposition

| Finding | Implemented change / consumer | Regression coverage | Remaining boundary |
|---|---|---|---|
| F01 local Codex config exported | Path-aware local config rejection plus reviewed exact `quality/export-policy.json`, enforced by validator AND packager. | `test_distribution_lifecycle` full public-validate/package/extract lifecycle. | Independent secret scan and maintainer distribution review still required. |
| F02 retrieval scope used as integrity | `file_policy.integrity_files` is separate; task/CI fingerprints include locks, configs, excluded evals, private/binary/large inputs and executable modes. | `test_hardening_regressions`, `test_retrieval_integrity`. | Tracked sources retained even under build-like roots; tracked runtime state rejected; posthoc detector, not sandbox. |
| F03 disconnected governance | `governance.references` resolves required evidence; task-bound workflow/ref/command pins feed preflight, reserved local counters and postchecks. | `test_governed_execution`. | Opt-in; unbound tasks marked NOT_CONFIGURED. No remote identity, global billing or OS authority. |
| F04 CI approval conflation | `seed_acceptance.py` and required scope job separate from technical checks; protected narrow discovery-only exception. | `test_feature_acceptance`, `test_ci_gate`. | Local approval files are not authenticated; protect checks externally. |
| F05 unbound feature flows | Explicit feature registry feeds all active feature docs into approval and existing doc/code/test paths into context. | `test_feature_acceptance`. | Spec semantics and actual test coverage still need review/execution. |
| F06 dropped abstention | One normalized PREDICTED/ABSTAINED/ERROR protocol across adapter, envelope and scorer. | `test_prediction_protocol`, `test_hardening_regressions`. | Provider claims are not automatically true. |
| F07 ignored policy | Strict policy schema rejects unknown/missing fields; coverage is required and enforced. | `test_prediction_protocol` tests bound low-coverage runs explicitly. | Comparator is review screening, not a statistical equivalence guarantee. |
| F08 orphan provenance | Saved run binds dataset, candidate/config, executor, predictions and manifest in one envelope; scoring verifies it. | `test_prediction_protocol` CLI roundtrip and tampering/relabel probes. | Hashes are not signatures. Legacy raw lists are exploratory only. |
| F09 retired mirror persists | Preview and apply known unchanged mirror retirement; edited/orphaned copies block and remain intact. | `test_distribution_lifecycle`. | Restart/inspect actual native discovery afterward. |
| F10 uncovered Python source | AST symbols plus uncovered module-level range chunks. | `test_hardening_regressions`, `test_retrieval_integrity`. | Other languages remain text-only; documented indexing limits remain. |
| F11 weak relation priority/duplicates | Semantic edges precede containment; generated Claude mirrors excluded from canonical context. | `test_hardening_regressions`, `test_retrieval_integrity`. | Declarations are not proven call graphs or test coverage. |
| F12 unbounded single-line reads | Serialized-character budgets, exact continuation offsets and digest checks on read/search/symbol/relations; explicit handoff limit. | `test_retrieval_integrity` reconstructs escaped Unicode source and rejects changed revision. | Characters are not tokens; transport wrappers have overhead. |
| F13 CI profile conflation | Maintainers test shipped MCP; app applicability explicit; retained starter checks cannot be replaced by app check list. | `test_feature_acceptance`, full profile smoke, `test_ci_gate` 64 combinations. | Real OS/client/cloud behavior needs external runs. |
| F14 repeated argv rejected | Array semantics allow repeated values and empty non-executable arguments. | `test_hardening_regressions`, shared supervision tests. | Only reviewed shell-free argv is intended. |
| F15 candidate child leakage | Shared bounded process supervisor for tasks, CI, candidates; POSIX session cleanup even after leader exit. | `test_supervision` confirms a child started before proving cleanup. | Escaped sessions and full Windows containment require OS facilities. |
| F16 stale phase/activation | `doctor` consumes current scope, source/CI/task hashes and optional client records; distinguishes recorded/current/stale/not-needed/not-verified. | `test_feature_acceptance`, `test_client_evidence`. | Local evidence is not independent certification or a finished-app declaration. |
| F17 misleading current docs | README, evals, contributing, MCP, CI, execution, approval, upgrade and publication guides reconciled to implementation. | Static links and `test_documentation_contract`; clean CLI journeys. | Semantic documentation review remains necessary. |
| F18 no real client verification | Stronger official-SDK semantic checker, native-client scenario matrix and evidence consumer. | Fixture/record unit tests exercise local semantics; external runs are NOT claimed. | Official SDK transport, installed clients and hosted jobs remain explicitly NOT_RUN/BLOCKED here. |

## Boundaries joined by this release

```text
Feature registry → scope evidence → revision-bound approval → task/scope checks
Governed task → workflow/data/eval/recovery pins → preflight → bounded execution
Candidate → normalized status → bound run → scorer → strict review policy
Canonical skill → create/update/retire → discoverable client mirror
Source → distinct integrity / retrieval / reviewed-export policies
CI profile → retained starter + actual app + applicable MCP + scope → final gate
```

A second-order portability issue was fixed too: planner-bound approval can reference a
reviewed source snapshot in a clean CI checkout. Temporary reconstruction rechecks the
same evidence without copying live leases or creating a second authoritative store.

## Activation, not compulsion

UI, marketing, sales, predictive evaluation and multi-session maps remain optional. Do not
turn everything on to make a dashboard green. Use one applicable consumer and explicit
reason/evidence per capability. Technical PASS, current approved scope, connected client,
and deployed behavior are separate facts. Standalone tools can be used intentionally,
but are never silently certified as governed merely because their schemas exist.

## Independent verification still needed

The local runner cannot prevent an unrestricted client shell from bypassing it. Protect
source/evaluator/policy ownership, scope credentials and isolate commands. Hosted GitHub
rules are not enabled by a ZIP. Synthetic tests do not establish model quality, interview
quality or cost savings. The release is a candidate pending actual deployment/client checks.
