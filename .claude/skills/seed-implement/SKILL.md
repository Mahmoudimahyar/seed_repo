---
name: seed-implement
description: Implement an approved feature or bugfix in small tested slices, with explicit scope and recoverable checkpoints. Not for initial unspecific discovery.
---

# Implement

## Prepare
Read the approved task, relevant contracts, current source and actual test commands.
Confirm permission, scope and workspace ownership. For a new app, check recorded readiness
and actual user approval. Use relevant native/retrieval tools, but never assume an MCP
index is present or fresh. Do not read the entire repository by default.

## Build
Follow docs/workflows/implementation.md. Write meaningful behavior/regression tests first
where appropriate, confirm expected failure, implement minimally, and verify. Record
justified exceptions. Reuse existing solutions, honor module boundaries and privacy,
and avoid unrelated refactors or speculative architecture. UI requires real flow tests
when possible; unavailable capabilities are NOT_RUN/BLOCKED. Diagnose failures rather
than blindly patching. Continue approved slices without an infinite no-progress loop.

## Finish the slice
Review specification compliance and code quality separately. Apply seed-simplify to changed
code, rerun checks, update affected docs, and save revision/commands/results/next action.
Do not release, merge through protections, or deploy production without appropriate approval.

## Revision-bound scope
For initialized applications, keep `readiness_sha256` in executable task plans equal to the
current approved readiness binding and use its exact scope. The runner checks before and
after each command. A required decision becoming stale also blocks continuation. Do not
mutate frozen specifications to track progress: keep execution checkpoints separately.
A changed contract needs review and reapproval, not a forged new fingerprint. Never treat
an isolated prototype or a resolved planning ticket as production approval.

## Integration contract

For declared governed tasks, bind the exact workflow, reference hashes and argv/cwd request before execution; require_governance forbids unbound tasks. A denied preflight is not a reason to bypass the runner. Technical checks and recorded scope acceptance are separate; preserve both. Integrity scans include lock/config/evaluation inputs even when retrieval excludes them.

## Reused dependency evidence
Use public supported APIs before custom wrappers or copied internals. For tasks materially
based on registered external source, include the current `seed_oss.py bind` object in the
plan's `external_sources`; require reviewed mapping for version-specific adoption. The runner
checks actual cache/evidence freshness before/after steps and resume. First-party retrieval
exclusions do not exempt external evidence from those explicit checks. No new dependency or
external data transfer is authorized merely because source is available.

## Spec-anchored TDD
List scenarios, implement one meaningful failing test at a time, make it pass, then refactor.
Do not prewrite the entire speculative test suite or move testing to a final phase. Update
mutable reports rather than PASS cells in approved plans. Classify discrepancies using
specifications-and-tdd.md; obtain new approval for material scope, not ordinary internal
refactoring. Existing public APIs can satisfy a contract with less code.
