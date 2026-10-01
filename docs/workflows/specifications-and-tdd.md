# Spec-anchored development with TDD

Approved specifications establish intended behavior. Code/runtime behavior establishes what
actually happens. Tests and reviews provide selected evidence. None automatically overrides
the others. Do not add a second constitution hierarchy or overlapping SDD plugin.

## Scale the process to the change

Already-authorized small fixes and internal refactors use the current contract. Multi-session
uncertainty can use [decision planning](decision-planning.md); major scope changes use the
existing change proposal and [approval binding](approval-binding.md). Authorized disposable
probes settle feasibility without becoming production code automatically.

For meaningful ambiguity, describe preconditions, trigger, observable result/side effects,
safe failures, invariants and representative counterexamples. Distinguish binding constraints
from explanatory sketches. Reference the actual OpenAPI/JSON Schema/etc. instead of maintaining
another description of the same fields. A requirement is not an instruction to create a
factory, service, wrapper or new dependency. Research/reuse still comes before custom code.

## TDD loop

1. Identify relevant behavioral scenarios from the approved scope.
2. Pick one. Write its executable test and run it: failure must be for the intended behavior,
   not an unavailable dependency or malformed harness.
3. Implement the smallest passing change. Refactor while it remains green.
4. Repeat; exercise applicable integration/browser and broader regression checks.
5. Compare outcomes against the contract and reconcile discrepancies.

This is not all tests up front, code-first test generation, or an uncontrolled full-product
build. Supporting implementation tests may emerge during TDD. Documentation/configuration
and generated code use appropriate verification, not pointless unit tests.

## Keep approval stable while evidence changes

Active feature files and gate evidence are revision-bound. Never turn a test-plan cell from
NOT_RUN to PASS: doing so changes the material that was approved. Record test execution in
.seed-local, .seed-ci-artifacts, or an independently managed CI artifact. A persistent reviewed
summary must stay outside the registered specification roots. Material changes to intended
behavior require a proposal and actual reapproval; updating execution results does not.

Use [requirement verification](requirement-verification.md) when machine-checked mappings are
worth the cost. It is optional and scoped; ordinary projects keep their existing test runner.

## Reconcile the right artifact

| Observation | Resolution |
|---|---|
| Implementation violates approved behavior | Fix code and regression coverage. |
| Test asserts the wrong result | Correct it against reviewed intent, not the faulty implementation. |
| Specification is contradictory or incomplete | Resolve the question; amend and reapprove material scope. |
| New feature is requested | Scope separately or defer; do not quietly add it. |
| Internal design changed but public behavior did not | Keep the contract stable and verify the refactor. |

Record this in the existing validation report/PR. No new standing agent or report hierarchy.
A test link does not prove a meaningful assertion; independently review high-risk contracts,
examples and counterexamples. Business adoption metrics often belong after release, not in
a fictitious pre-release passing test.

## Existing applications

Reconstruct provisional contracts using code, tests, docs and stakeholders. Label observed
behavior, documented promises, inferred intent and approved intent separately. Establish
characterization tests before risky changes, but distinguish a preserved baseline from a bug
that needs a corrective regression test. An old workaround is not automatically a new rule.
See [integration](../maintainers/integrating-existing.md).

## Evidence of benefit

This release tests local mechanics, not comparative agent effectiveness. Evaluate against the
unchanged workflow on matched tasks and permissions: missed requirements, defects, review effort,
rework, total cost and unnecessary ceremony. More markdown or more passing tests is not the
objective. See [source and design record](../research/specification-sources.md).
