# Resume after a closed session

Open the same checkout and paste:

```text
Resume this project without overwriting prior work. Read AGENTS.md, seed.json,
current project scope/readiness, the active task, and recent verification notes.
Inspect Git status, recent commits, uncommitted changes, and actual tool availability.
Do not trust a previous "done" statement without evidence.

Use exact source paths and native search first. If an MCP/GraphRAG server is actually
connected, verify freshness and use it for relevant code/document relationships.
If unavailable, state that and use the documented fallback; do not invent tool calls.

Report the current stage, completed versus unverified work, blockers, active test
configuration, and next safe task. Run the smallest relevant non-destructive checks.
Ask only for unresolved decisions that block progress. If scope is approved and no
blocker remains, continue one tested slice at a time, simplifying and reviewing the
diff, updating evidence, and preserving a clear next action for interruption recovery.
```

Keep resumable checkpoints concise: task/issue ID, scope, revision or dirty-tree details,
changed files, commands/results, current failure, and next action. Never copy raw secrets
or a whole session transcript into permanent instructions. Shared task status belongs in
one issue/PR system when available; link to it rather than maintaining conflicting ledgers.

## Interrupted decision planning (0.3+)
Run `python scripts/seed_plan.py handoff --map MAP --ticket QUESTION` or use the read-only
planning_handoff MCP. Several maps require explicit selection; never choose by recency.
Inspect current evidence, prerequisites, claims and exceptions. Reclaim only after expiry
or explicit release. Restore a reviewed snapshot only into an absent map ID. References
and signatures are not real approval. See [planning](workflows/decision-planning.md) and
[approval migration](workflows/approval-binding.md).
