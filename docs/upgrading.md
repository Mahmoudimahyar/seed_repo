# Upgrading a project that uses Seed Repo

A template copy is an independent repository, not an automatic subscription to upstream
changes. Do not fetch and overwrite its instructions, docs, CI, license, or application.

Record the starter version from `seed.json`. For a desired update, compare the old/new
release on an isolated branch, read the changelog, and apply only relevant changes.
Maintain the project's approved decisions and permission boundaries. Update canonical
skills first, regenerate supported mirrors, run template-tooling tests and application
checks, and review the result before merging.

An existing application may not retain every template file. Use the existing-repository
integration guide and adapt checks intentionally rather than restoring a giant scaffold.
Avoid merging unrelated Git histories simply to receive template updates.

Changes to skills, prompts, routing, or evaluators require behavior evaluation where
applicable. A new upstream model/tool recommendation does not authorize new spending,
data transfers, changed licenses, or production deployment.

## 0.2.0-rc.1 to 0.3.0-rc.1
Integrate on a reviewed branch; preserve the app, Git history and local configuration.
Update scripts/seed.py, scripts/seedlib, schemas, changed skills and docs together. Regenerate
Claude mirrors with `python scripts/seed.py sync-skills --write` after resolving local edits.
Readiness schema 1 is intentionally BLOCKED. Preview `seed.py migrate-readiness`, then
apply `--write` to preserve the old record and clear approval. Follow the revision-bound
approval workflow; do not invent consent to restore a green gate. Add `readiness_sha256`
and exact scope to application task plans. Existing template users need no readiness migration.

Decision maps remain opt-in. No remote backend is installed. MCP adds one read-only
`planning_handoff` tool; reinstall reviewed requirements if necessary, restart the server,
rerun check_mcp.py, then verify the actual client. Do not replace an existing `.mcp.json`.
See [release notes](releases/0.3.0-rc.1.md) for boundaries and validation status.

## 0.3.0-rc.1 to 0.3.1-rc.1 — integration hardening

This release tightens several contracts. Integrate scripts, schemas, CI/profile configuration,
canonical skills and relevant docs together on a reviewed branch. Preserve application code,
`.mcp.json`, `.codex/config.toml`, credentials, private data, Git history and modified instructions.
Do not run the initializer again or blindly replace the active app check configuration.

1. Install/review requirements-dev.txt; optional MCP dependency remains separately installed.
2. Add `quality/scope-policy.json`, updated `quality/template-checks.json`, retained tooling tests
   and the CI profile logic. Keep real app commands in `quality/seed-checks.json`.
3. For initialized schema-2 projects, preview `python scripts/seed.py migrate-features`, then
   apply `--write` after review. It adds the features gate/registry and clears old approval.
   For schema 1, perform the documented readiness migration first. Template mode needs neither.
4. Register each active feature and fill its artifacts. Explicitly defer irrelevant features.
   The existing application is not automatically assigned owners or approved scope.
5. Record MCP applicability with `configure-mcp --enable` or `--disable`, a meaningful `--reason`,
   and `--write`. Reconnect only when intended; do not delete existing servers.
6. For clean CI with planner requirements, attach a reviewed sanitized snapshot as documented
   in approval binding. Recheck source/decisions, generate a new proposal, obtain real review,
   and record that evidence. Never manufacture approval merely to restore green status.
7. Update task `scope`/`readiness_sha256`; add workflow/request/reference bindings for governed
   tasks. Old execution fingerprints intentionally do not resume under the new integrity policy.
   Confirm no worker runs, preserve/archive old state/logs, reconcile work, and rerun necessary
   checks with an approved plan. Do not rewrite old hashes to pretend fresh execution.
8. Reindex context: the format changed. Sync canonical skills with preview and then --write.
   Retirement of known unchanged generated copies is now handled; edited/orphaned mirrors block
   for manual reconciliation. Restart the client and actually verify discovery/MCP semantics.
9. Regenerate candidate-run outputs using the new envelope. Legacy arrays remain exploratory;
   they cannot qualify for promotion. Add the required min_coverage policy and remove/fix unknown
   fields only after a real policy decision, not to lower the acceptance bar.
10. Run retained tooling tests, app checks, separate scope acceptance and applicable MCP/client
    scenarios. Test the real hosted workflow and protection settings before rollout.

The maintainer exact distribution inventory belongs to the upstream starter publish checkout,
not to automatic publication of downstream app contents. Update it only after file-by-file review.
See [integration changes](integration-hardening.md) for finding-level coverage and limits.

## 0.3.1-rc.1 to 0.4.0-rc.1 — optional source research

Integrate on a branch; do not initialize an existing app again. Preserve application code,
local client configurations, credentials, customized skills, and active test commands.

1. Integrate the external-source scripts/schemas, tool policy, changed approval/task/status code
   and retained tests together. Install the existing `requirements-dev.txt` if not available.
2. Add the empty registry only if missing; NEVER overwrite an existing registry. Absence or an
   empty registry requires no source-related approval migration. Populating it changes evidence
   and requires actual scope review. Existing readiness/task schema versions remain compatible.
3. Resolve canonical skill edits, preview `sync-skills`, then apply `--write`. No new upstream
   skills, hooks, MCP tools or mandatory model dependencies are added. Do not run graphify install.
4. Enable providers only for useful research. Use a dedicated environment/pinned package, run
   the real provider checker, and keep local paths out of commits. Source acquisition remains
   UNVERIFIED until identity is checked and mapping reviewed; do not approve by version label.
5. For managed tasks using external source, add `external_sources` from `bind`. Changed plans or
   source require inspected recovery/new approvals as relevant, not editing old checkpoint hashes.
   Older tasks with no external-source bindings continue to operate without this capability.
6. Run starter regressions, application tests and scope checks. Run real provider tests separately
   on supported systems; absence is not a reason to pretend tests pass or block unrelated work.

Public starter maintainers add reviewed new files to the exact distribution inventory; downstream
applications should not use that inventory to publish their own private content. Provider version
updates require checking the pinned API, dependency/license/security changes and real acceptance.
See [external-source guide](workflows/external-source-research.md) and the release boundary.

## 0.4 to 0.5: specification verification and public upload candidate

No mandatory schema migration, client configuration replacement, dependency install or new
project feature is required. Keep existing source research, planner and approval capabilities.
Merge template/skill changes on a branch; do not overwrite project documents.

Move mutable outcome cells out of approved test plans through a reviewed edit. That edit
correctly changes approval fingerprints: obtain real reapproval, never rewrite old hashes.
Execution reports outside scope then no longer cause approval churn. Internal code refactors
still do not independently require specification reapproval.

The optional verification.json filename in active feature roots now has a strict contract.
Before opting in, use namespaced requirement headings, the actual reporter's case identities,
and a fresh {junit} output path. If an existing unrelated file already uses that name, relocate
or adapt it through review rather than silently reinterpreting it. Other legacy prose/table
ID styles remain supported without a verification map.

Use --profile for integrated application CI. It retains starter tests and executes enabled
feature maps after successful app checks. A bare custom-config run remains technical-only.
Keep manual checks and post-launch outcomes distinct. See the new specification workflow and
0.5 release notes; no performance or token-reduction gain is assumed from this upgrade.
