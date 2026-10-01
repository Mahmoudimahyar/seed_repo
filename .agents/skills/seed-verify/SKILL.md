---
name: seed-verify
description: Verify results before claiming a task is done, fixed, passing, integrated, or released; distinguish evidence from declarations.
---

# Verify before completion

## Execute
Identify the task's acceptance contract, current revision, actual commands and relevant
flows. Run the appropriate checks in a safe environment; keep command exit status, tests,
assertions, and full logs available. Template checks never substitute for app acceptance.
No secret dumps or production side effects to obtain evidence.

## Evaluate evidence
Classify PASS/FAIL/BLOCKED/NOT_RUN and documented non-applicability honestly. A schema-valid
response is not factual proof; a config file is not a connected server; a passing mock is
not a real integration; a screenshot is not persistent-state verification. Check coverage
against requirements, not only aggregate green output. Protect independent evaluators.

## Report
Use templates/validation-report.md. Include scope, revision/environment, commands/results,
source evidence, changed docs, remaining risks and next action. Never fabricate CI links,
human approval, browser runs, token savings, or benchmark rankings. Record what was not run.

## Integration contract

Run the separate scope acceptance check in addition to relevant technical checks. Use docs/testing/client-acceptance.md for real native-client scenarios. Invocation alone is not conformance; retained generated files and configuration alone are not connected integrations. Oversized captured output is an explicit failure, not silently complete logs.

## Executed requirement evidence
For a feature opting into verification.json, run/check scripts/seed_trace.py and use the
application --profile CI path. Preserve missing, skipped and manual checks as unverified.
Inspect assertions and important counterexamples; mapped IDs and local hashes are not
semantic proof or authenticated attestations. Complete the reconciliation section of the
existing report without changing frozen specification files merely to record progress.
