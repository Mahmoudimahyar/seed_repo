---
name: seed-debug
description: Investigate a reproducible bug, failed test, flaky behavior, or unexpected output using evidence before fixes.
---

# Debug systematically

## Reproduce and isolate
Preserve user work. Capture expected/actual behavior, minimal reproduction, relevant
revision/configuration, and safe logs. Identify whether failure is in code, contracts,
data, permissions, environment, dependency behavior or the test itself. Check existing
known issues without assuming the old explanation still applies.

## Test hypotheses
Form one specific hypothesis, run a narrow experiment, and record the result. Do not
add random retries, swallow errors, or relax tests to manufacture a pass. Use a stronger
model or specialist review only when evidence and task difficulty justify the cost.

## Verify
Apply the smallest correct fix, add a regression case, and rerun relevant integration
or browser paths. Escalate a real decision/permission blocker or repeated no-progress
failure with evidence. Record remaining uncertainty and next action, not a fake completion.
