# Purpose, workflow authority, data access, and decision evidence

These are original Seed Repo implementations inspired by the reviewed ExO concepts,
not a redistribution of the book or uploaded skill packages. The objective is safe,
understandable execution, not mandatory corporate structure or agent proliferation.

## Purpose before tactics
Use `templates/purpose.json`: outcome, hard constraints, preferences, non-goals, and
worked decision scenarios. A hard privacy constraint cannot be outweighed by a speed
score. The template's purpose is not imposed as the user's product mission. A CLI may
need only a few constraints. Store observed workflows separately from proposed behavior.

During discovery ask for normal examples, exceptions, recurring decisions, dependencies,
friction, and expert judgment. Validate old workarounds rather than blindly automating them.
Turn approved scenarios into tests. Do not treat historical decisions as verified truth.

## Workflow and data contracts
Use `templates/workflow.json` and `templates/data-access.json`. Record a human owner,
allowed actions/paths/hosts, resource budgets, memory boundary, applicable evaluations,
escalation queue owner/capacity/timeout, and recovery behavior. Reassess every reuse scope.
Data manifests record fields, authoritative source, sensitivity, permitted recipients,
retention, terms, training permission, and dispute owner. User data stays private by default.
Public template maintainers receive no project data or telemetry automatically.

```bash
python3 -m pip install -r requirements-governance.txt
python3 scripts/seed_governance.py validate --kind workflow examples/governance/workflow.json
python3 scripts/seed_governance.py validate --kind data-access examples/governance/data-access.json
python3 scripts/seed_governance.py preflight --workflow examples/governance/workflow.json --request examples/governance/request.json
```

Schemas reject missing fields, additional fields, empty owners, and unfinished templates.
The preflight checks action/host/path scope, read-only restrictions, consumed/projected
budgets, exact-request approval digests and expiry, and the local emergency stop flag.
It DOES NOT authenticate a person, verify remote data terms, enforce network isolation,
reserve resources atomically, or replace a trusted execution gateway. Protect policies,
counters and approval evidence outside the worker's control. Bind approvals to exact
request bytes/configurations; never accept a universal `approved: true` for arbitrary work.

## Safe stopping and recovery
`python3 scripts/seed_governance.py stop` creates a local stop signal without demanding
an explanation. The local task runner checks it before actions and while waiting for
commands. This is not remote revocation: separately stop cloud jobs, revoke credentials,
and compensate irreversible side effects. Record reasons after stopping when necessary.
Clear it only after investigation with `resume --acknowledge`.

## Decision records and review queues
`schemas/decision.schema.json` records scope, evidence, policy hash/version, actual
approver, outcome, exceptions and expiry. Exceptions need expiry; executed/failed actions
need an observed-result reference. A prior exception is not new policy. Store concise
rationale and runtime evidence, NOT hidden model reasoning, secrets, or unrestricted chat.
Use trusted append-only storage for production audit; JSON files are not tamper-proof logs.
A queue contract is not a hosted queue: integrate GitHub issues or an existing operations
system, assign accountable reviewers, limit inflight work, and block on timeout/full capacity.
Never increase worker authority to bypass an overloaded review queue.

## Learning and governance verification
Trusted evals, searchable safe logs, granular recovery, and a staffed review path are
separate operational capabilities. Test each. Lower override rates alone do not prove
quality: audit agreements, workload mix, coverage, escaped errors and human effort.
Shadow execution cannot observe a counterfactual action that was never taken. Separate
historical replay, verified evaluation, development examples and synthetic edge cases.

## Referenced evidence and the execution consumer (0.3.1)

Preflight now resolves every `data_manifest`, `evaluation_refs`, recovery reference and optional
`purpose_ref`. References must be safe, existing nonempty files; data/purpose are validated and
the data manifest must belong to the workflow. A path to a report does not prove its claims are
true or that its tests passed. Protect and review the source of that evidence separately.

```bash
python scripts/seed_governance.py references --workflow examples/governance/workflow.json
```

The output is a hash map for the complete referenced set. Pin it and the workflow in a task's
`governance` binding. See [execution](execution.md). Tasks with a binding consume preflight before
running; `require_governance` rejects unbound tasks. Direct scripts/client shell calls that bypass
this runner are not certified by it. The local executor reserves counters within one locked plan;
it is not a multi-plan provider-spending authority. Configuration alone is not integration.
