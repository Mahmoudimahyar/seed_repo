# Human and agent access

## Agent capability boundary
Thousands of agent workers must not share an organization-owner PAT. Prefer a GitHub App
integration with selected repositories, short-lived installation tokens and narrow roles.
Separate coding, trusted policy/check publication, release and deployment identities.
Workers receive only needed capabilities; an orchestrator can broker writes and retain
per-task attribution. Not every worker needs a distinct GitHub user. Size installation
permissions and scope honestly: a contents-write token is not path-level sandboxing.

Coding workers can propose changes, push assigned branches and open PRs. They do not
change rulesets, ownership, security exceptions, environment approvals, secrets, or
production release policy. They may propose changes to protected policy via reviewed PRs.
A controller/runtime, not a markdown instruction, enforces which tokens and environments
workers can access. Prevent self-approval and implementer control of trusted acceptance.

GitHub worktrees and branch rules do not isolate a local worker from host credentials.
Use least-privilege execution containers/VMs; isolate ports, temporary DBs, caches and
network access. Keep App signing keys at the controller. Read-only reviewers use isolated
credentials. A PR from a known agent is still untrusted code until accepted.

## Actions
Default GITHUB_TOKEN to read-only; job-level write permissions only where justified.
Never execute untrusted PR source, scripts, packages, or downloaded artifacts in privileged
pull_request_target/workflow_run jobs. Avoid those events in the starter. Do not inject
PR titles or issue bodies into shell scripts; read them as data. Pin external actions and
reusable workflows to verified full SHAs and update via reviewed dependency PRs.

Use hosted ephemeral runners initially. At scale, self-hosted runners require ephemeral
isolation, separate trust pools, network restrictions, reliable cleanup and no persistent
cloud credentials. Never put fork PRs on a persistent privileged runner. Source archives,
traces, artifact uploads and caches can also carry secrets or hostile payloads.

## Protect the judge
The ordinary seed CI adapter and PR tests are repository-controlled and can be modified
by a PR; they are not an independent adversarial boundary. Protect those paths with owner
review. At organizational scale, require a platform-owned workflow or external policy
App that checks exact source revisions, uses a pinned policy revision, and publishes its
own required check. Do not let the implementation agent issue the same trusted check.
If platform plan features are absent, do not claim equivalent enforcement; retain human
review, document the gap and choose an appropriate plan/external control when required.

Risk labels authored by contributors, PR checkboxes, agent summaries and self-reported
costs are advisory. Derive policy from trusted metadata/diffs and verified evidence.
A stronger LLM review is still probabilistic and does not replace these controls.

## Dependency and data policy
Use dependency updates, license review, lockfiles, secret scanning/push protection and
vulnerability scanning available on the actual plan. Use approved open-source scanners
where native capabilities do not fit. Document severity decisions, exceptions, owners and
expiration. Not every vulnerability automatically blocks unrelated work, but silently
ignoring one is never the policy. Avoid two dependency bots generating duplicate PRs.

Keep secrets, raw sensitive prompts, private evaluation examples, full browser recordings,
production data, large model weights and graph index caches out of Git. Store approved
manifests, schema, digest and access references instead. Configure artifact retention.
Choose repository/application license explicitly; public source is not automatic reuse
permission. Adopt snippet/dependency provenance from the reuse-first policy.

## Emergency changes
Human-only, time-limited, audited break-glass access with incident linkage, bounded scope,
post-change verification and review. No standing bypass for every bot/admin. Exercise
credential revocation, ownership recovery, artifact rollback and backup restore.
