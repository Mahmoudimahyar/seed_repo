# Security

## Reporting

Do not report exploitable vulnerabilities, credentials, private documents, or identifying
logs in public issues. On the published repository, use **Security → Advisories → Report
a vulnerability** when private vulnerability reporting is enabled. The maintainer must
enable and test that channel before public launch. If it is unavailable, use GitHub's
private reporting/support facilities or a maintainer's published private contact channel;
do not post exploit details while arranging a private channel. No private email address
or unverified security inbox is embedded in this template.

Include the affected release/commit, impact, minimal redacted reproduction, and suggested
mitigation. A prerelease has no guaranteed support SLA. The latest release candidate is
the current maintenance target until a stable support policy is published.

## Threat model and boundaries

This repository supplies executable scripts and agent instructions. Inspect them before
use. Instructions are context, not a security sandbox. The check runner executes
repository-configured commands with the invoking process's privileges and environment.
On POSIX, timeouts terminate the launched process group; on Windows, termination of every
descendant is not guaranteed. Use isolated runners/containers for untrusted code.

The starter does not contact a telemetry service or load/print `.env` values. Integrity checks may hash private input bytes locally without exposing their values. Configured commands,
third-party coding clients, MCP servers, and logs have their own data-handling behavior.
Gitignored files can still be read by an agent with filesystem permissions. Apply real
permissions/sandbox controls when necessary. Do not place production credentials in PR CI.

Changes to CI, agent instructions, skills, evaluators, dependency sources, and MCP config
are security-relevant. Review retrieved material as untrusted data, keep least-privilege
identities, and require authorization for network-side effects and production actions.

The local validator catches selected suspicious filenames and token patterns. It is not a
complete secret scanner, malware detector, license auditor, or proof of safety. Scan the
final Git tree and relevant history with approved tooling and manually inspect before
publication. A checksum detects file changes; it does not establish publisher authenticity.
