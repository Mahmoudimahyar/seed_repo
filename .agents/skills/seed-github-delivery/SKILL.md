---
name: seed-github-delivery
description: Prepare a scoped branch and pull request, review CI evidence, or execute an explicitly authorized release procedure. Never auto-publish a private project.
---

# GitHub delivery

## Prepare
Read CONTRIBUTING.md and docs/engineering/github-operating-model.md. Confirm actual repo,
branch, task, owner, permissions and uncommitted state. One writer per isolated task/workspace.
Stage explicit changes or review a clean distribution's full dry-run before bulk staging.
Use coherent commits and a Conventional Commit PR title. No direct protected-main push,
shared credentials, blind force push, or rewriting shared history.

## Verify and review
Run real scoped checks and fill the PR template with evidence. Protect CI/evaluators,
permissions, agent rules, shared contracts and ownership files. Require appropriate
independent review; never forge a human approval. Check actual GitHub status and merge
queue/settings rather than assuming YAML applied server-side rules.

## Release only when authorized
Follow docs/maintainers/publishing.md for the template or the app's approved release policy.
Use one version authority, immutable release tags/artifacts, least privilege, and rollback.
Do not change visibility, spend money, publish, deploy, or execute destructive changes
without the necessary authorization. Missing credentials or account capabilities are blockers.

## Public template publication
Maintain the uninitialized starter, not a private application's working directory. Follow
docs/maintainers/publishing.md, keep hidden instruction/workflow files, verify the extracted
ZIP, and publish only after actual hosted checks and authorization. Stage only reviewed files;
never make a repository public or move an existing release tag implicitly.
