# Operating model: scalable practices, modest initial infrastructure

## Decisions
Use a GitHub organization for company ownership when ready; do not transfer an existing
repository without authorization. Have at least two accountable human owners when the
team permits, strong authentication, recovery procedures, and least-privilege team roles.
Start with one product monorepo if it remains the agreed layout; do not split into many
services/repos just because future headcount is large. Isolate repositories when access,
release ownership, scale, or regulatory boundaries justify it. Git file paths are not
read-access security boundaries: repository read permission exposes repository contents.

Use protected main + short-lived branches + draft PR + review + CI + queue/merge. No
permanent branch per person, agent, model, or environment. Maintenance branches are only
for explicitly supported release lines. Use feature flags for incomplete safe-to-merge
work; flag owner, expiry, cleanup issue and tested combinations are required.

## Work ownership
GitHub issue = authoritative shared task identity; PR = change and review; commit =
snapshot; tag = version marker; release = published notes/assets; deployment = an artifact
running in a specific environment. Avoid duplicating their status in multiple markdown
files. Documents define durable specifications/contracts/decisions; agent logs link them.

Every task has an accountable human/team, acceptance criteria, allowed scope, dependency
IDs, and verification plan. Exactly one writer owns a branch/worktree. Read-only reviewers
can be parallel. Changes to shared APIs/schemas precede consumer work. Worktrees isolate
working directories, not processes, credentials, ports, databases, or malicious code.
Use separate containers/VMs and isolated test resources where appropriate.

## PR gates
1. Approved requirement and correct scope.
2. Required tests and checks pass on the relevant combined revision.
3. Qualified review; fresh approval after meaningful new changes.
4. Policy/security exceptions explicitly recorded, approved and time-limited.
5. No unresolved material discussion, conflict, or undocumented rollback risk.

Use one independent reviewer for ordinary team PRs. Use stricter review for CI, security,
permissions, billing, data deletion, shared contracts, and evaluators. AI review helps
reviewers but is not automatically equivalent to accountable independent approval.
Authors cannot lower their own review policy by labeling a change low risk. At scale,
derive a conservative risk class from trusted path/policy rules, with reviewed overrides.

A list of code owners on one line requires any one owner, not all. Distinct security and
domain approvals need a trusted policy check outside contributor control. Protect the
CODEOWNERS file, tests/scorers, setup scripts, instructions, model registry and workflows.

## Merge policy
Use squash merges and Conventional Commit PR titles. A complete independently reviewable
change is the unit, not a timer or arbitrary file count. Preserve necessary attribution.
Use merge queue once contention justifies it and the account supports it. Every required
workflow must handle merge_group, not merely pull_request. The queue validates integration
but cannot detect a missing requirement absent from its tests. Keep candidate/task
relationships visible, particularly for ordered migrations or stacked PRs.

Without a merge queue, require current base + successful checks and a serialized merge
process. After merging, delete only the completed task branch when safe. Revert through
PR; do not reset/rewrite main. Hotfixes use the same safeguards with expedited review,
not a secret bypass. Backport only to supported lines and test that line's dependencies.

## Solo phase
A sole human cannot independently approve their own PR. A consciously approved solo
profile may use zero required reviews while retaining PR/check/tag protections and
manual risk review. Mark that assurance gap explicitly. Switch to team policy as soon
as an independent reviewer exists; do not grant bots permanent bypass to simulate it.
