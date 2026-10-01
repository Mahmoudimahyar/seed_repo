# Capability and evidence status

Current candidate: **0.5.0-rc.1**. Run `python scripts/seed.py doctor` for local evidence-derived
status. `seed.json.phase` is an explicitly labeled historical hint, not live truth.

The doctor distinguishes applicability, availability, configuration, recorded freshness, and
external verification. It does not install, connect, spend, publish, or print credential values.
Integrity checks may hash private file bytes locally; hashes are never copies of their contents.

| Piece | Consumer / activation | What does NOT count as verification |
|---|---|---|
| Features | Registry → scope approval → code/test links in context | A planned test filename is not coverage. |
| Approvals | Scope checker and application task runner | A locally edited approver name is not authenticated consent. |
| Governance | Explicit task binding; require_governance for all-task plans | Standalone schemas or preflight do not govern bypassed shell actions. |
| Evaluation | Candidate envelope → scorer → strict comparator | Synthetic demos or consensus are not verified ground truth. |
| Context | CLI and optional read-only MCP | Index/config presence is not freshness or native connectivity. |
| Planner | Explicit selected map → decision snapshot/approval → task scope | A lease is not an execution/spending authorization. |
| Skills | Canonical sources → checked client mirrors → native scenarios | Successful sync is not behavioral conformance. |
| CI | Retained tooling + applicable app + separate scope/MCP jobs | Technical PASS alone is not final acceptance. |
| Publishing | Public validation → exact reviewed export → extracted checks | File hashes are not a signature or security audit. |

Optional UI/marketing/sales/AI can remain NOT_NEEDED. No task map is created without need.
MCP is required for upstream maintainers and explicitly optional for apps. Missing configuration
is BLOCKED rather than guessed. Current command evidence does not infer that an app is complete.
A safe client acceptance record can be consumed, but locally recorded outcomes remain untrusted
until appropriately reviewed. Hosted GitHub/cloud protections remain NOT_VERIFIED here.

No live-model leaderboard, paid scheduler, automatic consequential promotion, secret-scanning
certification, hosted graph service or thousand-worker control plane is claimed. See
[validation](validation.md), [audit closure](integration-hardening.md), and the workflow guides.

## External research capability
`integrations.external_sources` reports NOT_CONFIGURED, REGISTERED, STALE or BLOCKED, with
per-source freshness, snapshot identity, mapping status, and graph NOT_BUILT/BUILT/PARTIAL/STALE.
It is a read-only local view and does not call/install an upstream provider. The tracked registry
is optional and empty in the public starter. Provider runtime acceptance remains separate from
snapshot freshness; run `check_external_tools.py` explicitly. Source/task consumers and boundaries
are described in [external research](workflows/external-source-research.md).

## Optional requirement verification
The active feature registry remains authoritative. A registered verification.json opts that
feature into structural requirement/reference checks and application-profile execution. The
doctor reports PLANNED/NOT_CONFIGURED/BLOCKED, not an assertion of tested behavior. Per-run
results preserve skipped/missing/manual/post-release distinctions and source freshness. No
new default framework, model, MCP operation or test-runner dependency is introduced.
