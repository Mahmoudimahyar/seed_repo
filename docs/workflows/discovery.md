# Discovery: resolve intent before application code

## Intake and scope

Read the user's supplied material first. Distill confirmed facts, assumptions, conflicts,
and open questions without publishing private source documents. Identify the project mode
and capabilities. Marketing and sales are explicit opt-ins; UI and model use are independent
capabilities. A project name/type is not permission to invent a website, billing, or user accounts.

Ask a small set of high-value questions, usually three to five, not a fixed exhaustive
survey. Use prior answers and documents before asking again. For a meaningful choice,
present a researched recommendation, viable alternatives, tradeoffs, reversibility, and
whether the choice blocks the active scope. The user can delegate reversible technical
choices within their stated constraints.

## Research and decisions

For consequential or uncertain decisions, compare the established baseline with emerging
approaches and record primary sources, version/revision, checked date, relevant evidence,
tradeoffs, and a refresh trigger. New does not mean best. Evaluate maintained libraries
or services before custom implementation. Research should resolve a decision, not collect
links for appearances. Reuse valid findings until their assumptions change.

## Buildable specification

Before implementation, the active scope needs an outcome, non-goals, users/workflows,
input/output contracts, main states and failure modes, permissions/data requirements,
external dependencies/configuration, observable acceptance criteria, and a test mapping.
Define modular boundaries and data ownership without making every function a reusable
framework. Record feasibility uncertainty; small isolated experiments need their own
scope and are not permission to start the application.

For UI projects, create one global map plus detailed feature flows with stable route/flow
IDs, preconditions, expected persisted effects, errors, empty/loading states, access denial,
responsive behavior, and matching test cases. CLI projects use commands, exit codes,
stdout/stderr, examples, and terminal-flow tests instead.

## Approval and continuous gaps

After each round, update only affected documents and the gap list. Distinguish blockers,
accepted risks, and intentionally deferred questions. Show the scoped build plan and test
strategy to the user. Record their actual approval in the readiness record, with an
accountable name and a reference to an approval note. Do not manufacture consent.

`seed.py ready` checks recorded completeness, paths, placeholders, and approval fields.
It cannot assess correctness, verify identity, or enforce behavior across agents. Use it
alongside human review and stronger permissions where required. Do not demand omniscience:
resolve the next build scope and identify what would invalidate it.

## Optional dependency-aware planning
For multi-session uncertainty, use [decision planning](decision-planning.md). Small clear
work bypasses it. Separate accepted behavior from proposed changes and review whole-system
invariants. Before application implementation, use [revision-bound approval](approval-binding.md)
to bind real acceptance to current evidence; unbound schema-1 readiness is no longer valid.
