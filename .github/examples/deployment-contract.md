# Deployment workflow contract (not runnable deployment)

Required inputs: approved artifact digest, source SHA, release/config reference and target
environment. Never accept a free-form shell command, unchecked branch URL or mutable latest.

1. Verify trusted artifact provenance: digest, expected repository, workflow and source/ref.
2. Verify intended environment, release order, approval and rollback compatibility.
3. Acquire short-lived OIDC cloud credentials in a separate deploy job for that environment.
4. Deploy the already-built artifact. Do not rebuild a different artifact for production.
5. Run schema compatibility checks, sandboxed smoke tests and controlled rollout checks.
6. Halt or revert according to measured health thresholds and the approved rollback plan.
7. Record deployment ID, digest, source, config reference, results and operator/approval.

Use native provider deployment actions/APIs or the existing deployment tool; do not build a
custom deployment engine. Use a platform-owned/pinned reusable workflow at scale.
Do not name an environment and assume it is protected. An admin must configure and verify
protection, and the cloud trust policy must be narrow. Current GitHub docs changed default
OIDC subject formats for newer repositories; inspect actual claims without exposing tokens.

An environment gate is plan-dependent. If unavailable, use an approved external release
controller or a supported plan; workflow_dispatch alone is not independent approval.
The deployment target was not supplied for this kit, so production setup is intentionally
BLOCKED rather than represented by a fake deploy-success command.
