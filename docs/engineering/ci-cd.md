# CI profiles and acceptance boundaries

`.github/workflows/seed-ci.yml` handles PRs, main pushes, merge groups and manual runs with
read-only default permissions and retained reviewed action pins. Hosted execution is a
separate verification step; local parsing is not proof those protections are active.

## Three required job groups

| Group | What must succeed |
|---|---|
| `checks` | Configured platform matrix: retained starter regressions plus applicable app checks. |
| `mcp` | Maintainer or explicitly enabled app: install SDK and run semantic protocol checks. Disabled app: successful explicit NOT_APPLICABLE record. |
| `scope` | Template: NOT_APPLICABLE. App: current bound approval, or narrowly authorized documentation-only exception. |

`seed-ci-required` requires success from ALL three. The shell truth-table test covers all
64 combinations of success/failure/cancelled/skipped. The MCP job is not skipped wholesale:
it validates applicability first. Missing application applicability is BLOCKED. Protect the
actual check and its workflow/config origin through GitHub settings and independent review.
A contributor-controlled check cannot authenticate its own approver.

## Configuration

`seed_ci.py --profile-info` reports the selected profile without probing connectivity.
`seed_ci.py --profile --config quality/seed-checks.json` always runs
`quality/template-checks.json`, then app checks for an initialized project. The application
file begins BLOCKED until real commands are wired. Both starter and app reports are retained.
A bare `seed_ci.py --config ...` deliberately reports technical checks only; it does not
claim integration or approval. The scaffold's platform matrix is a starting policy, not a
promise that every future application supports every OS.

`seed.py configure-mcp --disable --reason "Approved CLI uses direct source lookup only."`
previews the choice; add `--write` after review. Use `--enable` when the app uses the adapter.
This does not install/configure the actual server. Changing applicability invalidates bound
scope approval. Maintainers cannot opt out of testing a shipped adapter through this flag.

## Scope acceptance

`python scripts/seed_acceptance.py` checks recorded scope separately. It refuses unapproved,
stale or incomplete applications. `--ci` obtains a concrete base commit from GitHub's event
payload. The supplied `quality/scope-policy.json` permits unapproved discovery-only changes
under named documentation roots and the two specific discovery records. It does NOT permit
application/source/workflow changes. Diffs include staged, unstaged and untracked paths locally.
An absent/unfetchable base cannot grant an exception. The policy itself must be protected.

For planner-dependent approval in clean CI, include a reviewed, sanitized planner export in
the approved evidence (see [approval binding](../workflows/approval-binding.md)). CI reconstructs
a temporary view and rechecks source/policy hashes without writing the authoritative local DB.
A private local planner database that CI cannot access cannot be assumed valid.

## Evidence and security

The runner preserves exit status, bounded logs, dependency/config/source fingerprints and
command outcomes. Failed setup makes later checks NOT_RUN. Missing commands are BLOCKED.
Logs have a shared capture limit; exceeding it is FAIL/OUTPUT_LIMIT, not a truncated PASS.
No PR title or issue text is interpolated into a shell. Do not inject provider/cloud secrets
into untrusted PR code. Governed external evaluations need a separately approved execution
boundary. No real application, hosted protection, cloud deployment or native client has been
certified merely by installing this workflow.

For CD use a trusted build, immutable artifact/digest, staging verification, controlled
promotion and recovery. Record relevant source/model/prompt/tool/data versions. The starter
contains policies and examples, not credentials or a universal production deployer.

## Opted-in specification verification (0.5)
After successful application checks, --profile automatically executes registered active
feature verification.json maps. Supporting failures, skipped/missing mapped tests and stale
source cannot produce covered PASS. If the application checks already failed, these checks
are NOT_RUN. No maps means explicitly NOT_CONFIGURED, not fabricated coverage and not a new
mandatory test-framework dependency. The normal scope job still checks current approval.
See [requirement verification](../workflows/requirement-verification.md).
