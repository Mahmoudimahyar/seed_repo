# Release automation: implement after target discovery

Recommended default: release-please for a mixed-stack/co-deployed release unit; evaluate
Changesets for independently published JavaScript packages. Do not enable both for the
same release unit. Review current upstream docs, releases and supported package strategies;
pin selected actions to full verified SHAs. Do not invent a package.json or registry.

Design the release workflow for trusted main only. Separate the release-PR identity from
build execution and the package publisher where feasible. Handle the GITHUB_TOKEN event
suppression behavior using a narrowly scoped App or explicit tested dispatch. Never give
the bot bypass for protected main merely to get automated release PRs merged.

The resulting release must tie tag/version -> exact approved source -> build workflow ->
immutable package/container digest -> provenance/SBOM -> test/evaluation evidence.
Validate permissions, publication idempotency, version uniqueness, tag restrictions,
prereleases, failed publication, and recovery in a sandbox registry/repository.

No publisher workflow is supplied as runnable YAML: the application/package target,
registry, credentials and release units must be discovered before safe activation.
