# Scaling from a team to a company

Start now: protected main, isolated task branches, clear owners, CI, scoped tokens,
reviewable release automation and tested rollback. Defer thousands-worker orchestration,
Kubernetes runners and complicated multi-repo governance until their cost is justified.

At contention: add merge queue, task-dependency scheduling, component ownership, tested
affected-project selection, isolated test infrastructure, and build caching with trust
separation. Use native APIs/webhooks; authenticate webhook signatures and handle duplicate,
out-of-order and redelivered events idempotently. Respect rate limits and Retry-After;
prefer event-driven reconciliation to each agent polling GitHub continuously.

At organizational scale: platform-owned reusable workflows versioned and pinned,
organization rulesets, centrally governed App installations, immutable artifacts,
external/central verification identity, isolated runner pools and bounded budgets.
A standard GitHub organization `.github` repository can share defaults, but never assume
every policy file is automatically inherited/enforced; verify actual repository settings.
Keep custom properties/service ownership metadata explicit and audit configuration drift.

A scheduler needs task leases (with expiry), branch/run IDs, dependency edges, retry
budgets, conflict detection, per-team/repository quotas and backpressure. Freeze dispatch
when review/CI backlog exceeds the agreed capacity. Do not create thousands of speculative
PRs faster than the organization can validate. A merge queue does not repair bad task
boundaries or decide which product requirements matter.

Track lead time, review wait, queue wait, CI duration/cost, flaky-failure rate, change
failure/rework, recovery time, rollback success, security exceptions, and owner load.
For agents add accepted change per total cost, escaped regressions, scope violations,
retry/escalation rate and human review effort. Do not reward lines generated, commit count
or number of PRs. Count research/inference/runners/cache/storage and human cleanup costs.

Service/library independence, access boundaries, and measurable build contention determine
when to split a monorepo. Headcount alone does not. Shared schemas and cross-repo changes
need a compatibility/release protocol even when source is in separate repositories.
