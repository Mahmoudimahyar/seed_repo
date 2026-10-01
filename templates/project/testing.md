# {{project_name}}: test and acceptance plan

## Acceptance mapping
__FILL__

## Appropriate test layers and actual commands
Specify unit, integration/contract, build, regression, and relevant browser/CLI/API tests.
Record a reason for each genuinely inapplicable category. Do not create pointless tests
or use success-only commands to pass a gate.
__FILL__

## Fixtures, isolation, providers, and secret handling
__FILL__

## Critical negative paths and expected observable results
__FILL__

## Evidence and release policy
Separate PASS, FAIL, BLOCKED, NOT_RUN, and documented non-applicability. Define what requires
human review, how failures stop release, and which evaluator artifacts need protection.
__FILL__

## Plan versus results
This document is approved intent, not a progress log. Store changing results in execution
reports. List scenarios up front, then follow one failing test -> minimal implementation ->
refactor. Appropriate manual acceptance and post-launch outcome measurement remain separate
from executable release checks. Optional feature verification.json maps are consumed by
application CI; do not claim requirement coverage from an aggregate test count alone.
