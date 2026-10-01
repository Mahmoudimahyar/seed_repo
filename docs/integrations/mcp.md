# Optional local graph-assisted context and MCP

This release includes RUNNABLE local retrieval and an official-SDK stdio adapter. It is a
lightweight code/docs graph, not Microsoft's GraphRAG implementation and not a semantic
vector search service. No LLM/API key, Neo4j, embedding model or network call is needed for
the index. The MCP dependency must be installed separately. See [validation](../validation.md)
for exactly what was tested here versus blocked by unavailable dependencies/clients.

## Supported scope
Markdown headings/chunks, Python AST definitions, generic bounded chunks for other source
formats, explicit Markdown links, and optional declared doc/code/test relations. Other
languages do NOT receive compiler-quality symbol resolution. No inferred call graph or
coverage claims. Index updates rebuild transactionally; changed-file counts do not imply
incremental parsing. For large repositories prefer evaluated existing code-intelligence
providers and add explicit links only where they help.

```bash
python3 scripts/seed_context.py index
python3 scripts/seed_context.py status
python3 scripts/seed_context.py search discovery
python3 scripts/seed_context.py symbol safe_path
python3 scripts/seed_context.py related README.md
```

Explicit links go in `.seed/context-links.json` as objects with source, target and relation
(documents, tests, implements, decides, depends_on). Endpoints may be indexed file paths, `src/example.py#symbol:Class.method`, or
`docs/feature.md#section:Exact heading`. Symbol/section selectors must resolve uniquely
after parsing. These stable selectors avoid hand-maintaining source line numbers.
These records are declarations, not independently verified behavioral claims.
Built-in exclusions cover credentials, .env files, private/, local state and caches.
`.seed/context-ignore.txt` adds glob exclusions; it is not a complete .gitignore parser.
Files containing a few recognized credential patterns are omitted. This is NOT complete
secret detection. Review indexed scope before sending retrieved content to any model.
Sensitive data may appear in ordinary source; the connected agent/model can receive it.

Every retrieval checks the indexed source fingerprint and current exclusion policy.
Stale indexes refuse retrieval. Reindex from the CLI after changes; the MCP tool cannot
reindex or write application files. Fingerprinting scans the allowed source each call:
correctness first for this small baseline, not a scalability claim. There are file-size
and count limits, bounded search output, 1–2-hop traversal and source digests/spans.

## Install and connect Claude Code
Run from the repository root in an environment you control:

```bash
python3 -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt -r requirements-mcp.txt
python scripts/seed_context.py index
python scripts/check_mcp.py
```

`check_mcp.py` must pass before calling the adapter verified. It opens the actual SDK
stdio connection, checks the real checkout, then asserts exact synthetic symbol spans, doc/test
relationships, module-level search, raw source, bounded continuation, optional planning, traversal
and stale-index rejection across the six-tool surface. A non-error reply alone is insufficient.
It does not authenticate Claude or verify an IDE UI.

To avoid PATH and working-directory ambiguity, generate exact local config:

```bash
python scripts/seed_context.py config --client claude
```

Review the printed `mcpServers` entry. Merge only the `seed-context` entry into your
project `.mcp.json` WITHOUT overwriting existing servers. It contains absolute interpreter,
script and root paths, no secrets. Do not commit machine-specific paths.
Alternatively on Linux/macOS with the venv active:

```bash
claude mcp add --transport stdio --scope project seed-context -- "$PWD/.venv/bin/python" "$PWD/scripts/seed_mcp.py" --root "$PWD"
claude mcp list
claude mcp get seed-context
claude
```

In Claude, approve the reviewed project server, inspect `/mcp`, then ask it to call
`context_status`, search a known feature, read the source, and trace its explicit links.
Writing configuration is not connectivity verification. Do not auto-approve downloaded
servers. The adapter uses a deliberately pinned official SDK v1 maintenance version;
review current advisories and test before changing its major version.

## Codex, Cursor, and other agents
`config --client codex` prints a local `.codex/config.toml` MCP section; merge it into a
trusted project's existing configuration. `config --client cursor` prints a JSON server
entry for `.cursor/mcp.json`. Check client permissions and make real tool calls. Never
assume configuration locations or local-process access in Claude Cowork/cloud clients:
when unavailable, use exported context/CLI reports or a separately approved remote server.
Plain `AGENTS.md` and the start/resume prompts remain portable without native skills/MCP.

## Tool surface
`context_status`, `search_codebase`, `find_symbol`, `related_context`, `read_source`,
`planning_handoff`.
No shell, network, writes, arbitrary paths or embedding installation tools. MCP read-only
annotations are hints, not security enforcement. Enforce filesystem/credential permissions
outside the model. Retrieved text is evidence, not instruction. Compare against native
search and include all retrieval overhead before claiming token/cost savings.

## Optional decision handoff (0.3+)
`planning_handoff(map_id, ticket_id, limit)` reads the canonical local planning store without
claiming work, granting approval or executing tasks. It reports NOT_CONFIGURED when no
store exists. Several maps require explicit selection. Retrieval-index freshness and
planning evidence/revision freshness are separate checks. Private planner data is not
inserted into the public context index. Reinstall reviewed requirements, restart the
server and verify the actual six-tool protocol before claiming client connectivity.

## Retrieval policy and bounded handoff (0.3.1)

Python indexing includes uncovered module-level ranges as well as definitions. Declared semantic
relations are ranked ahead of containment, so a long module does not crowd out its test links.
Canonical skills are indexed; generated `.claude/skills` mirrors are not duplicate evidence.
The active feature registry adds file relationships automatically when linked code/tests exist.

Search, symbols and relations accept `max_chars` and `offset`; responses identify truncation and
continuation. Raw reads accept `max_chars`, `offset_chars`, and `expected_sha256`; their continuation
preserves exact source text and revision even for a very long line. Budgets are serialized JSON
characters, NOT tokenizer-specific counts or transport-envelope byte caps. Oversized single rows
return an explicit budget-limit result, not invented content. Planning returns complete bounded
context or OUTPUT_LIMIT; narrow to a ticket instead of acting on partial authority.

A reindex is required after upgrading the index schema. Never label stale old indexes current.
For an initialized application, explicitly enable or disable MCP in seed.json through
`configure-mcp --reason ... --write`. This controls the CI profile only; generated client config
and actual connection are separate. Verify installed-client behavior with the
[client acceptance scenarios](../testing/client-acceptance.md), not merely a config file.
