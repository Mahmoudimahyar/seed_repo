# Finalized requirements coverage

This release consolidates the latest decisions, not every superseded instruction in the
conversation. Status distinguishes runnable tools, workflow guidance and configuration
that requires real accounts/infrastructure. None implies a future app is already tested.

| Requirement | Implemented home | Status and boundary |
|---|---|---|
| One public ZIP, README and download/template onboarding | README, START_HERE, publishing guide, package_release.py | Executable packager; no public GitHub repo created here. |
| Any app/tool, without forced stack or marketing | seed.py init, seed.json, mode/capability templates | Tested initializer; scope explicitly selected. |
| Interview documents before coding; continuous gap questions | seed-discovery, workflows/discovery, project templates/readiness | Tested recorded gates; an LLM/human must conduct the real interview. |
| Current research, stable vs frontier options, decisions/ADRs | seed-research-reuse, research-decision template, source register | Workflow; no indiscriminate research daemon or fabricated sources. |
| Open-source/APIs before custom code; licenses/costs/reliability | research/reuse and dependency templates | Workflow; current candidate selection remains project-specific. |
| Deterministic first, specialized models before larger agents | benchmarking/design policies and builtin extractor | Runnable baseline; cannot universally automate domain judgment. |
| Small readable code; simplification after tests | seed-simplify and implementation guide | Review workflow, not line-count minimization. |
| Modular interfaces, dependency boundaries, contract tests | architecture/features/test templates, implementation skill | App-specific enforcement tool selected for its stack. |
| TDD, integration/contract/regression/UI tests | skills, test matrix templates, CI adapter | Starter tests run locally; future app/browser tests need the app. |
| Global website map and per-feature flows | ui-scoped project templates and feature/ui-flow | Generated only for UI scope. |
| Reusable accessible brand/components/assets across channels | seed-design, design-system and asset-register templates | Recipes; actual visual identity/assets need user direction. |
| On-demand roles/skills, multi-agent compatibility | canonical .agents, checked Claude mirrors, Cursor/Copilot adapters | Files tested; installed client discovery is separately verified. |
| GStack/Superpowers/Hermes lessons without plugin bloat | focused skills, recovery, reviewed improvement | No third-party plugin or copied archive auto-installed. |
| Local GraphRAG-style docs/code/tests retrieval | seed_context.py, seedlib/context.py | Tested local graph/lexical retrieval, Python AST, explicit edges. |
| MCP integration and proof it works | seed_mcp.py, check_mcp.py, generated local configs | Implemented SDK adapter; see validation for dependency/client test status. |
| Freshness, privacy exclusions, bounded retrieval | context fingerprints, exclusions, 1–2 hop/size limits | Tested; not a full secret scanner, compiler graph or semantic search. |
| No guaranteed 70% token saving | status, benchmark/retrieval policies | No unmeasured cost claim. Compare real task costs. |
| Persistent progress, resume and bounded loops | seed_tasks.py and schema, recovery skill | Tested local DAG/checkpoints/locks/budgets, not a hosted agent fleet. |
| Parallel branches/worktrees and safe shared-state boundaries | GitHub operating model, execution workflow | Policy; workers/runners/permissions depend on host. |
| Per-task probabilistic evaluations | seed_eval.py, run_candidate.py, exact/entity scorers | Runnable saved-prediction/external-adapter pipeline, not a live model leaderboard. |
| Cost/latency, coverage, slices and uncertainty | evaluation metrics, conservative comparison | Executable; representative-data assumptions and self-reported provider cost are explicit. |
| Strong-model consensus with human review | consensus command and label provenance | Consensus remains provisional; agreements also require audit. |
| New-model reevaluation and reviewed promotion | evaluation/skill lifecycle and comparison reports | Review proposals only. Paid schedules/promotion require approved provider deployment. |
| Recursive skill improvement | seed-improve, old/new/held-out comparisons and mirror sync | Evaluated PR workflow; no self-approval daemon. |
| ExO purpose as constraints and scenarios | purpose schema/template; discovery extension | Strict schema; scenarios still need actual eval execution. |
| Tacit operating knowledge and subtraction before automation | discovery/reuse/governance workflow | Explicit normal cases, exceptions, dependencies, friction and judgment. |
| ExO authority and data access manifests | workflow/data-access schemas, seed_governance.py | Tested strict contracts/preflight; trusted identity/counters still external. |
| Decision evidence, exception expiry and ownership | decision schema, governance guide | Tested schema; local records are not tamper-proof audit logs. |
| Emergency stop without prior justification | stop command and managed runner checks | Tested local stop; remote actions need actual revocation/compensation. |
| Review queues, safe timeouts, rollback and correction capture | workflow contract/governance and GitHub workflows | Contracts/guides, not a hosted operations queue. |
| Standard Git, commits/PRs, tags/releases and CI | .github and engineering docs, package_release.py | Local checks/configuration tested; hosted enforcement must be activated. |
| Least privilege, protected evaluators and approval boundaries | SECURITY, engineering/access, governance/CI policies | No agent can be made trustworthy merely with prompts. |
| Public license/notice, contribution and security reporting | LICENSE, NOTICE, CONTRIBUTING, SECURITY | Existing MIT scope retained; third-party rights remain separate. |

## Superseded rules deliberately not restored
No mandatory skill invocation before every answer; no full-document dump into context;
no GraphRAG dependency before every task; no always-on business/marketing department;
no endless repair loops; no model-consensus-is-truth rule; no unreviewed automatic skill
or consequential model promotion; no copying large third-party book/skill packs; no
mandatory enterprise structures, proprietary data platform or universal 10x threshold.

## What an adopter still supplies
Their actual product specification, selected dependencies, credentials, deployment target,
real acceptance datasets, role/approval identities, application tests, brand assets if any,
and provider/client integration verification. These are required inputs, not hidden
unfinished implementations of a universal application.

## 0.3.0-rc.1 decision-planning integration

| Accepted proposal | Implementation | Boundary |
|---|---|---|
| Optional uncertainty map, precise tickets, fog and exclusions | decision-map/ticket schemas, seed_plan.py, seed-wayfind | No map for ordinary clear work. |
| Deterministic references, cycles, outcome-aware eligibility | seedlib/planning.py + negative tests | Semantic sufficiency remains human/model judgment. |
| Source/decision revisions and dependent invalidation | Resolution signatures and transitive checks | Conservative byte-level evidence freshness, not semantic diff. |
| Revision-bound readiness and task continuation | approvals.py, seed.py schema 2, task application_gate | Recorded evidence, not authenticated authorization. |
| Exact recovery, current handoff and one authority | Explicit selection, bounded handoff, local SQLite, optional MCP read | No full transcript replay or silent dual-write tracker. |
| Local concurrent claims and history | Transactions, tokens, expiry, compare-and-set, event snapshots | One local filesystem, not a distributed lock. |
| Proposed versus accepted behavior and cross-feature review | Change/review templates, seed-plan-review and updated discovery | Reviewer must actually run; local tests do not prove model quality. |
| Portable handoff | Reviewed export/import without leases or overwrite | No remote synchronization, no signed trust certificate. |
| Evaluation scenarios | evals/wayfinding fixtures and deterministic regression cases | Live-agent paired evaluations NOT_RUN. |
| Optional external tracker | Documented backend contract | Deferred until a backend and authorization are selected. |

## 0.3.1-rc.1 integration-hardening coverage

The earlier rows identify capabilities; [the fixed-findings matrix](integration-hardening.md)
now identifies the consumers and cross-component regression tests. New executable boundaries
include active-feature scope registration, portable planner approval evidence, separate scope
acceptance, profile-aware retained tooling/MCP CI, governed task preflight, integrity fingerprints
independent of retrieval, bound prediction envelopes/strict coverage policy, safe skill retirement,
source continuation and exact distribution allowlisting. Native-client outcomes can be recorded
with current evidence but are not authenticated or assumed executed. External validation remains
explicitly required; see the current validation report.

## 0.4.0-rc.1 — optional verified dependency research

| Requirement | Implementation / consumer | Verification boundary |
|---|---|---|
| Reuse implementation evidence before custom code | Extended seed-research-reuse → seed_oss.py → public-API experiment → decision | No automatic install or universal benefit claim. |
| opensrc acquisition with version honesty | external_tools.acquire_opensrc + request/registry schemas | Always unverified; real-provider acceptance is separate from protocol doubles. |
| Exact source identity | Git-object export/fetch, snapshot digest, no ref fallback, explicit compare/restore | Git source projection is not proof of published package equivalence. |
| Optional Graphify structural navigation | Pinned AST worker → sanitized graph → bounded neighborhoods | No semantic backend, upstream installer, global hooks or first-party graph merge. |
| Existing scope/task integration | Approval evidence and external_sources plan/checkpoint bindings | Tracks current source/review; not human authentication or OS isolation. |
| Privacy/export | Dedicated .seed-local caches; empty public template registry | User-supplied durable reports still require review. |
| Comparison without fake results | evals/reuse scenarios and actual provider checker | Benchmark NOT_RUN; no runtime-certification claim from doubles. |

See [release notes](releases/0.4.0-rc.1.md) and [validation](validation.md).

## 0.5 specification-verification refinements

| Finalized requirement | Actual implementation | Boundary |
|---|---|---|
| Behavior contracts and examples, not speculative architecture | Existing requirement templates and discovery/plan-review skills | Human intent/semantic adequacy still need review. |
| Spec-anchored TDD | Existing implement/verify skills and specifications-and-tdd.md | Not a new agent framework or all-tests-upfront waterfall. |
| Mutable evidence separate from approved plans | Revised test-plan and validation/PR reconciliation templates | Editing intended rules still correctly stales approval. |
| Optional requirement-to-executed-test mapping | verification-map schema, seed_trace.py, spec_trace.py, feature lint and application CI | Exact IDs/status/freshness, not semantic proof or authenticated attestation. |
| No ignored enabled capability | Active maps consumed by --profile; doctor reports planning applicability | Bare technical checks do not claim integration coverage. |
| Legacy observed versus intended behavior | Existing-repo guide and discovery skill | Reconstructed intent remains provisional until accepted. |
| Clear public upload instructions | Updated publishing guide and current release notes | No public repo, remote protections or live deployment created by packaging. |
