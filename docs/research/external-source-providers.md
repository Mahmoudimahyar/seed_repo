# External-source providers: source/API review

Checked for the 0.4.0 release preparation on 2026-09-21. These are provider adapter targets,
not a claim that every current/future release is supported. This file is maintainer research,
not package suitability or license approval for downstream projects.

## Primary evidence

- opensrc reviewed revision: `b51de60867e806da1839b33dd29c29424f12521b`, npm package `opensrc@0.7.3`.
  [README](https://github.com/vercel-labs/opensrc/blob/b51de60867e806da1839b33dd29c29424f12521b/packages/opensrc/README.md),
  [package metadata](https://github.com/vercel-labs/opensrc/blob/b51de60867e806da1839b33dd29c29424f12521b/packages/opensrc/package.json),
  [Git acquisition](https://github.com/vercel-labs/opensrc/blob/b51de60867e806da1839b33dd29c29424f12521b/packages/opensrc/cli/src/core/git.rs),
  [fetcher](https://github.com/vercel-labs/opensrc/blob/b51de60867e806da1839b33dd29c29424f12521b/packages/opensrc/cli/src/core/fetcher.rs),
  [path command](https://github.com/vercel-labs/opensrc/blob/b51de60867e806da1839b33dd29c29424f12521b/packages/opensrc/cli/src/commands/path.rs).
  Acquisition can fall back to a default branch and strips .git. Warnings/cache labels are
  insufficient proof; the adapter makes no version claim on download. Explicit package version,
  separate OPENSRC_HOME, clean credentials and bounded command execution are used.
- Graphify reviewed revision: `20a20d30d8e7eef77675651f0199d87f913bd3e7`, package `graphifyy==0.9.65`.
  [Architecture](https://github.com/Graphify-Labs/graphify/blob/20a20d30d8e7eef77675651f0199d87f913bd3e7/ARCHITECTURE.md),
  [AST extractor](https://github.com/Graphify-Labs/graphify/blob/20a20d30d8e7eef77675651f0199d87f913bd3e7/graphify/extract.py),
  [package metadata](https://github.com/Graphify-Labs/graphify/blob/20a20d30d8e7eef77675651f0199d87f913bd3e7/pyproject.toml).
  The documented AST library accepts explicit paths/root/cache/parallel controls and returns
  node/edge provenance. Seed uses that narrow entry point, not semantic extraction or installers.
- Git's existing [archive](https://git-scm.com/docs/git-archive) and
  [fetch](https://git-scm.com/docs/git-fetch) interfaces provide a fallback acquisition path.
  Git export attributes apply; commit identity is not publisher artifact provenance.

## Decisions made for Seed

Keep current first-party context and MCP. External source is a separate namespace with explicit
registry identities. Use approved public interfaces after testing; source visibility does not make
private functions supported. Graphs are optional derived evidence. Licensing of dependencies and
any adapted code is reviewed separately; no upstream code or skill archives are vendored here.

Fixed model/token savings, provider security, and source-to-published-package equivalence are not
asserted. Real installation probes and matched A/B/C reuse scenarios remain required before
changing defaults. Changes in these libraries require a fresh API/source review and tests, not
merely bumping version strings in the allowlist. Version checks are compatibility checks, not
cryptographic verification of an installed provider or its transitive dependencies.
