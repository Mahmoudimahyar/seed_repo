# Workflow and policy files

Changes here affect the trust boundary. Follow the root AGENTS.md and CONTRIBUTING.md.
Keep least-privilege permissions, reviewed SHA-pinned actions, safe untrusted-input handling,
and an always-reporting required gate. Never run untrusted PR code with production secrets.

Do not claim rulesets, reviewers, merge queues, environments, OIDC, or release protection
are enabled because configuration files exist. Verify server-side state and failure cases.
No auto-merge/publish/deploy privileges are granted by these instructions.
