---
name: seed-govern
description: Define or review autonomous workflow authority, data access, decision records or emergency behavior. Not required for every routine edit.
---

# seed-govern


Read docs/workflows/governance.md. Extract purpose, hard constraints and decision scenarios.
Remove unnecessary steps and prefer deterministic/reused execution. For a recurring
workflow define a human owner, action/data boundaries, budgets, evals, escalation capacity,
stop/recovery and reuse scope. Validate schemas and preflight with seed_governance.py.
Local records do not authenticate a human or enforce OS/cloud permissions. Protect policy
and counters outside worker control. Record real evidence and approval scope/expiry;
never turn a one-time exception into lasting permission. Emergency stopping cannot require
a justification first. Ask for user intent or authorization where unresolved.

## Integration contract

Use seed_governance.py references to resolve the complete manifest/evaluation/recovery/purpose set. Bind those hashes and the exact command to governed task execution. Inspect recorded preflight and local reserved counters, but never call them authenticated provider billing or an OS sandbox. Direct unbound commands remain NOT_CONFIGURED, not governed.
