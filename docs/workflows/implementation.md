# Implement in bounded, recoverable slices

Start from approved scope and current source. Confirm the right repository, branch, task,
permissions, allowed changes, and actual test commands. Use one writer per workspace;
parallel work needs stable contracts and isolated resources. Recover interrupted tasks
before starting new work.

Write behavior/regression tests first where applicable, confirm they fail for the expected
reason, implement the smallest sufficient change, and run targeted checks. Pure documentation,
generated code, and some configuration changes need suitable verification rather than a
contrived unit test; record the exception. Test public behavior and real contracts, not only
an implementation-shaped mock. Never weaken an acceptance criterion to get green checks.

For UI changes, exercise approved flows with real browser automation and persistent-state
assertions when supported. Check relevant console/network failures, loading/error/empty
states, permissions, and accessibility. Screenshots supplement behavioral evidence. A missing
browser or external service is NOT_RUN/BLOCKED, not success.

On failure, reproduce, collect safe diagnostics, isolate the layer, test a hypothesis,
apply a minimal fix, and add regression coverage. Stop repeated no-progress repairs and
report the blocker instead of burning an unbounded budget. Use implementation loops for
persistence, not as a substitute for a reliable acceptance test.

Before finishing, simplify the diff, review specification compliance separately from
code quality, run appropriate broader checks, update changed docs/contracts, and record
revision, commands/results, remaining risks, and next action. No automatic public release,
production changes, destructive migration, new paid commitment, or secret exposure.

The CI runner writes `.seed-ci-artifacts/report.json`. It preserves command exits and
separates FAIL/BLOCKED/NOT_RUN. It does not independently establish adequate coverage,
authenticate reviewers, or prove that a selected command tests the claimed behavior.
Keep full logs outside the conversation, with redaction and permissions suitable to their data.

## Reconciliation and optional executable mapping
Follow [spec-anchored TDD](specifications-and-tdd.md). Keep mutable results separate from approved
plans. For opted-in features, application CI runs [requirement verification](requirement-verification.md)
automatically; planned IDs alone are not execution evidence. Resolve the correct artifact when
code, tests and intended behavior disagree, and reapprove material scope changes.
