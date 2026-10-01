# Validation report — 0.5.0-rc.1

Date: 2026-10-01. This release remains a candidate for public upload, not a claim of
hosted/client/provider certification or guaranteed application quality.

[Current local evidence](../validation/release-0.5.0.json) records the new release checks.
The separate ZIP verification file distributed alongside the archive records post-extraction
results and its exact digest. The archive cannot contain evidence of its own final ZIP hash.
Files such as validation/external-source-checks.json, external-cli-checks.json,
local-unit-tests.txt and hardening-findings.json are retained **historical** evidence from
0.4.0 or earlier. They must not be mistaken for current hosted acceptance.

## Executed locally before packaging

- Unmodified 0.4.0 baseline: **445 tests passed** in 96.520 seconds.
- Updated candidate: **519 tests passed** in 128.024 seconds, including **74 added tests**.
- **33 real CLI expected-result checks passed** in disposable copies. Intended blocked,
  failure and stale outcomes count as successful safeguard tests, not successful app behavior.
- The new JUnit pilot was exercised with **installed pytest 9.0.2**: a real incorrect exporter
  failed its preservation test, the corrected implementation passed two actual tests, a
  skipped mapped case blocked, a nonexistent mapped case blocked, and editing source made
  the previous result stale. Test execution did not rewrite the specification/test plan.
- Initialization, registration, no-overwrite behavior, optional MCP applicability, planned
  tests before implementation, requirement IDs, emergency stop, first-party context and
  the lack of automatic scope approval were exercised by actual CLI commands.
- Unit fixtures include labeled synthetic JUnit reports for parser/security/negative cases.
  They are not representations of real customer behavior or native coding-agent sessions.
- Existing tests for approvals, dependencies, graph retrieval, external-source adapters,
  packaging, skills, governance, model-result provenance and process handling remain.
- Public static validation, JSON/YAML parsing, schema validation, Python syntax and checked
  skill mirrors are verified. Pinned GitHub Action commit identities were rechecked with
  upstream GitHub refs; this is identity checking, not an independent action security audit.

The tested environment was Linux, Python 3.13.5, jsonschema 4.26.0, pytest 9.0.2 and Git 2.47.3.
The advertised Python baseline is 3.11; the hosted matrix must verify its configured interpreter
and platforms. pytest is an example application dependency, not a new starter requirement.

## External acceptance: blocked or not run

- `python scripts/check_mcp.py`: **BLOCKED** because the optional official MCP SDK is absent.
  It was not replaced with a fake protocol test. Dependency downloads were unavailable here.
- Real Graphify acceptance: **BLOCKED**, provider absent. opensrc acceptance without explicit
  network authorization: **BLOCKED**. opensrc is absent and Node is 22.16.0; the reviewed
  optional opensrc integration requires Node 24+. No upstream provider was installed here.
- Hosted GitHub CI/rulesets, native Claude/Codex/Cursor/Cowork sessions, Windows/macOS,
  browser/production deployments, live model comparisons and independent security audit:
  **NOT_RUN**. Follow their respective acceptance guides before advertising those capabilities.
- No public repository was created, no visibility changed, no commits pushed or tags published,
  and no provider account or charge was authorized by producing this archive.

## What these checks do not prove

Specification traceability is opt-in and uses a bounded explicit JUnit subset, not every test
reporter format. Mapped PASS means the named cases ran and passed under the recorded command;
it does not prove that assertions faithfully encode the intended rule or that all requirements
were discovered. Manual requirements stay unverified in this automated pilot; post-release
observations are not pre-release tests. Semantic review and authenticated approval remain
separate. No interview-quality, token-saving or cost-improvement claim is made.

Local hashes detect drift, not malicious rewriting by an actor able to edit both code and
records. A local approval record is not an identity system. Trusted test commands run with
caller permissions; shared subprocess controls and the Graphify Python guard are not an
OS sandbox. Use isolated environments, protected checks and appropriate network/filesystem
controls for untrusted execution. External source identity is not proof of published-package
mapping, license suitability or a working integration.

## Final artifact procedure

The maintainer packager validates the explicit distribution inventory, refuses existing output
archives, and creates MANIFEST.sha256 plus a ZIP checksum. Run validation and technical CI from
a fresh extraction, then compare every packaged entry again. Keep runtime evidence/caches out
of the distributed archive. Consult the separate final verification JSON for those exact
post-packaging results; if any required external check remains blocked, publish only with its
candidate status and accurate limitations.
