# Versions, releases and deployments

## Default decision
For the bootstrap kit or a single co-deployed application, use one Semantic Versioning
release train. Start at an appropriate initial version; do not change an existing product's
version to 0.1.0 just because this kit has a separate version. Declare the public compatibility contract
before claiming SemVer compliance. It includes APIs, CLI/config formats, reusable schemas,
and externally relied-on behavior. Internal commits are not all releases.

After a stable 1.0 contract, incompatible public changes require a major version, compatible
features a minor version, and compatible fixes a patch. Prereleases such as v1.5.0-rc.1
are explicit. State the pre-1.0 policy; never hide surprising breakage behind early status.
PR title examples: feat(search): add synonyms; fix(api): handle retries;
feat(api)!: remove legacy response. Human review validates actual compatibility impact;
a title cannot prove that a change is non-breaking.

Use release-please for a mixed-stack/single-release project when its supported strategies
fit; it proposes release PRs/changelogs from Conventional Commits. For independently
published JS/TS packages, evaluate Changesets. Select ONE release authority. Do not let
multiple bots independently update versions, changelogs, or tags.

Do not maintain independent package versions merely because a monorepo contains several
folders. Independent versions make sense when packages have independent consumers and
release contracts. Release-please supports monorepo configurations; use the real manifest
paths and review dependency/version propagation. Test release automation in a sandbox.

## Release sequence
1. A release tool proposes versions/changelog/migration notes in a PR.
2. Normal required checks/review apply; no release-bot bypass of main.
3. Build approved source with pinned inputs and attach provenance/SBOM/quality evidence.
4. Validate version uniqueness, tag target and source eligibility.
5. Publish via the narrowly scoped release identity; finalize assets before immutability.
6. Deploy the same digest through staging and approved production promotion.
7. Link release and deployment IDs, then monitor/rollback if health criteria fail.

Never move or reuse a published version tag. Protect updates/deletion separately from
creation; allow the release identity to create only the approved pattern. Where native
immutable-release controls are available, configure and test them as an additional layer.
A protected tag name does not prove an artifact was built from that tag.

## Event triggering trap
Events caused by the default GITHUB_TOKEN generally do not trigger another workflow
(exceptions include explicit dispatch events). A release PR created by such a token may
not automatically receive expected CI. Use a least-privilege GitHub App with the necessary
permissions or an explicit, tested dispatch design. Do not work around this by bypassing
checks. App private keys belong in a privileged controller, not arbitrary PR runners.

## Release identity
Record at least: release version/tag, source SHA, artifact digest(s), build workflow/run,
SBOM/provenance references, lockfile/dependency state, migration version, environment
configuration reference (never values), model/prompt/tool configuration, evaluation
manifest/results, retrieval index/data snapshot where behavior depends on them, approval
and deployment IDs, and rollback target. Reconstructing source alone is insufficient to
reproduce an AI-enabled system.

No release publisher is activated in this kit because the real packaging target, registry,
permissions and release strategy are not established. Follow the release automation
contract in `.github/examples/release-automation.md` during adoption.
