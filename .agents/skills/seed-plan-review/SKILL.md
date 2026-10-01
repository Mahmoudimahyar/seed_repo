---
name: seed-plan-review
description: Review a substantial proposed implementation plan against accepted outcomes, cross-feature invariants and test coverage. Skip redundant review of clear, already-approved small edits.
---

# Plan sufficiency and consistency review

Use templates/plan-review.md. Read the exact approved baseline, proposed change, decision
handoff, architecture, relevant flows and test mapping. Preserve one source of truth.

1. Run structural checks (`seed.py ready` or preapproval `approval-manifest`, and planner
   status when used): references, required records, dependencies and revision freshness.
2. Separately inspect semantics: ambiguous terms, conflicting requirements, missing failure
   scenarios, role/data ownership, API/CLI/UI consistency and end-to-end user journeys.
3. Work backward from each intended outcome. Which task and observable test establish it?
   Identify a counterexample where every listed task passes but the intended outcome fails.
4. Examine shared invariants across features. Local plausibility does not prove the combined
   system uses consistent permission rules, entity identities, lifecycle or error contracts.
5. Keep review independent of implementation where practical. Record evidence, unresolved
   blockers, accepted residual risks and reviewer identity. Never turn an LLM opinion into
   authenticated approval or report a requirements review as tests executed.

Research or ask focused questions only for unresolved consequential issues. Do not add
business departments, interfaces, dependencies or scope merely to make a plan look complete.
A material proposal revision needs new review; the recorded binding conservatively treats
any byte change in pinned evidence as stale. Hand off to the authorized human and then
seed-implement. Do not auto-approve, mutate evaluators, or invent passing browser results.

## Requirement precision and traceability
Check binding behavior versus illustrative design. Use requirement examples/counterexamples
and existing schema references rather than bloated prose. Optional verification maps must
cover declared namespaced headings; planned tests need not exist yet. Distinguish structural
lint, executed test evidence and human semantic review. Do not accept a generated mapping as
proof that its test assertion verifies the behavior.
