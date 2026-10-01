# Troubleshooting

## The terminal cannot find Python

Install Python 3.11+ from a trusted source. On Windows try `py -3`; on macOS/Linux use
`python3`. Commands run from the directory containing `seed.json`. The Python interpreter
for starter tooling does not choose your eventual application language.

## Initialization shows paths but creates nothing

Preview is the default. After reviewing the mode, capabilities, and paths, repeat with
`--write`. Avoid initializing an upstream maintainer checkout.

## Initialization refuses existing files or a changed CI configuration

This protects prior work. Review the conflict, preserve it, and integrate manually on a
branch. There is intentionally no `--force` reset option. An interrupted write can leave
partial state; inspect Git status and files before recovery.

## The CI gate is BLOCKED after initialization

Expected until real application checks are configured. The starter's passing tests do
not prove your app works. Wire the appropriate commands and documented non-applicability
in `quality/seed-checks.json`; do not replace checks with no-ops. The generic adapter checks
command execution, not whether an agent selected a sufficient test suite.

## A skill is missing or duplicated

Check that hidden folders were copied, run `python3 scripts/seed.py validate`, and verify
client configuration. Claude uses the generated `.claude/skills` mirrors; Codex uses the
canonical `.agents/skills`. Do not install duplicate copies globally and locally without
understanding the client's lookup rules. A mirror conflict needs manual reconciliation.

## The agent immediately starts writing the app

Stop it and point it to START_HERE.md and the discovery skill. Ask for scoped requirements,
research, architecture/contracts, flow/test mapping, and actual approval. Markdown is not
a sandbox; stronger controls require supported hooks or managed permissions in the client.

## GraphRAG does not appear

The local index and official-SDK adapter are bundled, but the optional SDK is installed
separately. Follow docs/integrations/mcp.md, build the index, run check_mcp.py, merge the
generated config and approve the server in your client. A missing SDK is BLOCKED, not a pass. A config
entry, shell command name, or successful startup alone is not a retrieval evaluation.
Use native search or exact source paths until a suitable integration is ready.

## READY looks too easy to obtain

It is a recorded-evidence checker, not a truth detector or authenticated approval service.
A contributor can edit its source/config just like ordinary tests. Protect review and
acceptance using real permissions and independent checks appropriate to your organization.

## Browser, cloud, or model tests cannot run

Record NOT_RUN/BLOCKED with the missing capability and risk. Do not assert a successful
UI flow, integration, deployment, or model benchmark on the basis of mocked evidence.

## Installing dependencies or activating PowerShell fails

Do not disable system-wide safety settings. After `py -3 -m venv .venv`, run
`.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` directly if activation
is restricted. Use that interpreter for commands and generated MCP config. Package
installation requires access to the approved package registry; offline failure is BLOCKED.

## External source or Graphify is BLOCKED

The optional capability does not install providers. Read the source-research guide, use the
reviewed executable/interpreter prefix and run `check_external_tools.py` explicitly. For the
Graphify worker, inspect `INTERPRETER -m pip show graphifyy` in the selected environment, then
check its version against `quality/external-tools.json`. Worker logs are not echoed wholesale
because they can contain foreign code or credentials. A partial graph is not a full extraction.
Use exact source search while fixing optional parsing or dependency support.

An opensrc success remains unverified. Compare with an exact Git snapshot; no tag/default-branch
fallback may authorize version-specific adoption. Changed source/graph/review is stale, not a
reason to patch an old task pin. Restore only a missing known snapshot, or inspect/quarantine a
stale one manually. Do not delete another process's lock. Local research caches and private client
configurations do not belong in public releases.
