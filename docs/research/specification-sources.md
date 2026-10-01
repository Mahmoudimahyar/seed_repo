# Specification workflow decisions — 2026-09-30

Basis: the supplied SDD review of Seed Repo 0.4.0-rc.1, which inspected the Paul Everitt /
DeepLearning.AI / JetBrains course and its written companion. The previous review used an
automatic-caption mirror, not frame-by-frame viewing. No transcript, book, upstream skill
implementation or third-party project is redistributed here.

Adopt spec-anchored behavior, incremental TDD, requirement examples/counterexamples,
reconciliation, and a narrowly scoped ordinary-runner/JUnit pilot. Retain existing project
constitution equivalents, decision planning, approval, research/reuse and GitHub controls.
Do not adopt a second spec tree, all-tests-upfront, tests-on-request, code-as-prose-regeneration,
fixed question counts, local direct-to-main merging, or compulsory whole-product generation.

Reference URLs (conceptual sources, not claims of integration/certification):
- https://www.deeplearning.ai/courses/spec-driven-development-with-coding-agents/
- https://github.com/https-deeplearning-ai/sc-spec-driven-development-files
- https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- https://newsletter.kentbeck.com/p/canon-tdd
- https://cucumber.io/docs/bdd/example-mapping/
- https://github.com/github/spec-kit

Current publication procedures checked against primary documentation:
- https://cli.github.com/manual/gh_repo_create
- https://cli.github.com/manual/gh_repo_edit
- https://cli.github.com/manual/gh_release_create
- https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository
- https://docs.github.com/en/actions/reference/security/secure-use

The exact retained checkout/setup-python/upload-artifact tags were re-read through the
GitHub API on 2026-09-30. Pin identity checks do not mean hosted workflows were executed.
The network-isolated execution environment could not install the optional SDK/providers.
