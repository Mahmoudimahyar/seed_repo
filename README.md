# Seed Repo

### Clear requirements. Small implementations. Verified results.

A **stack-neutral, public-template starter** for humans and coding agents. Start a tool,
CLI, API, library, research project, data pipeline or product without being forced into
a particular framework, marketing plan, cloud service or model provider.

**0.5.0-rc.1 — specification-verification and public-upload release candidate.** This is developer tooling, tested local examples and
workflow guidance, not a finished application or a hosted agent platform. Read the
[verification report](docs/validation.md) and [capability boundaries](docs/status.md).
No fixed accuracy, token-reduction, speed, cost or scale guarantee is made.

[Start a project](START_HERE.md) · [Claude setup](docs/agents.md) ·
[Public publishing](docs/maintainers/publishing.md) · [Requirements coverage](docs/requirements-coverage.md) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

## What happens next?

```text
Your idea and documents
  → scope-aware interview + decision-linked research
  → optional decision map for multi-session uncertainty
  → requirements, architecture, contracts, relevant flows and tests
  → actual user approval bound to the reviewed revision
  → small implementations, reuse and simplification
  → verified checks, reviewed PRs and controlled releases
```

The agent resolves unknowns rather than rushing into code. It prefers a tested API,
library or deterministic procedure over repeated model improvisation. Skills load only
when useful. Hard constraints outrank cost and convenience. Marketing/sales are opt-in;
UI documentation is generated only when requested. No plugins or paid services auto-install.

## Quick start

1. Choose **Use this template → Create a new repository** on GitHub, or extract the ZIP
   into a new empty folder. Fork when contributing to Seed Repo itself. Do not overwrite
   an existing app; use the [integration guide](docs/maintainers/integrating-existing.md).
2. Install Python 3.11+, Git and your coding agent separately. Run from the repo root:

```bash
python3 -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python scripts/seed.py doctor
python scripts/seed.py validate --public
python -m unittest discover -s scripts/tests -v
```

On Windows use `py -3` in place of `python3` before activating the environment. The initializer and basic context/scoring operations use the standard library.
Feature-aware scope/index checks, policy validation, execution, and the full suite require
the pinned JSON Schema dependency. MCP uses a separately optional official SDK.
Package installation needs internet access; no model credentials are needed for demos.

3. Open your agent in this folder and paste:

```text
Read AGENTS.md and START_HERE.md. I am using this template to start my project.
Do not write application code yet. Read my idea/documents, identify scope and
capabilities, research consequential decisions, and ask focused gap questions.
Do not add marketing, sales, UI or paid services unless approved. Propose project
initialization, specifications, contracts, test coverage and environment needs.
Record facts separately from assumptions. Show the active-scope build plan and
obtain approval before coding. Use fresh MCP context when enabled and useful;
otherwise use exact source lookup. Never claim unrun checks or integrations pass.
```

See [getting started](docs/getting-started.md) for optional manual initialization and
[agent setup](docs/agents.md) for Claude Code, Codex, Cursor, Cowork and manual fallbacks.

## Working tools included

| Area | What is executable | Important boundary |
|---|---|---|
| Project setup | Preview/write initializer, active-feature registry, evidence-derived doctor, scope acceptance | Specs and feature flows are revision-bound; a local record does not authenticate a human. |
| Decision planning | Optional local maps, outcome-aware dependencies, revisions, leases and handoffs | No remote tracker, model auto-resolver or permission escalation. |
| External research | Optional opensrc/Git snapshots, strict identities, source search and Graphify AST adapter | Providers install separately; source availability is not approved version mapping or a proven integration. |
| Repo context | Local graph index, bounded search, Python AST definitions, doc/code/test links, stale-index refusal | Other languages use text chunks; no embeddings or compiler call graph. |
| MCP | Read-only stdio adapter using the official Python SDK; real handshake checker | Install optional dependency; verify the client on your own machine. |
| Governance | Strict contracts, validated reference hashes, optional task-bound preflight, budgets and emergency stop | Ungoverned tasks are labeled; local counters are not provider billing, identity or a sandbox. |
| Evaluation | Bound prediction-run envelope, abstention/errors, exact/entity scoring, strict coverage/cost/regression policy | Integrity hashes are not signatures; demos cannot establish real model quality. |
| Execution | Local task DAG, bounded attempts/timeouts, lock, checkpoint/resume | Runs trusted commands; not a thousand-agent cloud scheduler. |
| GitHub | PR/issues, SHA-pinned CI, release packaging, Dependabot, ruleset examples | GitHub rules, identity, reviewer and cloud settings require activation. |
| Specification traceability | Optional feature/JUnit mappings, scoped ID lint, current-source results, automatic application-profile checks | A test reference or PASS does not prove semantic coverage or human approval. |
| Skills | Focused skills, generated mirrors and safe retirement, optional native-client acceptance records | Files/records do not prove client behavior; run the documented client scenarios. |

## Reuse an existing implementation before writing another one

The [external-source guide](docs/workflows/external-source-research.md) extends the existing
research skill with verified snapshots and optional Graphify structural evidence. Start with
`python scripts/seed_oss.py status`. Defaults do not install Node, Graphify or new MCP servers.
Literal reads are enough for small questions; graph analysis must justify its own overhead.
Use the [real provider checker](scripts/check_external_tools.py) on the installed tools before
claiming compatibility. The maintained application still uses supported public APIs and tests,
not copied internals or source-version guesses. See [external-source release notes](docs/releases/0.4.0-rc.1.md).

## Specifications and TDD work together

Keep approved intended behavior separate from mutable execution evidence. List scenarios,
write one meaningful failing test, implement the smallest passing change, refactor, and
reconcile actual results against the contract. Existing prose-based projects keep working.
For high-value executable mappings, opt into the [spec/TDD workflow](docs/workflows/specifications-and-tdd.md)
and [JUnit traceability pilot](docs/workflows/requirement-verification.md). No extra agent,
SDD framework, model, or test-runner dependency is imposed on the application.

## Turn on optional GraphRAG/MCP

The local graph is a lightweight retrieval implementation, **not Microsoft GraphRAG**.
It uses no model calls. For initialized projects, first record whether MCP is wanted (`configure-mcp --enable` or
`--disable`, with `--reason` and `--write`). The maintainer profile always tests the shipped
adapter. Install the official SDK only when MCP is wanted:

```bash
python -m pip install -r requirements-mcp.txt
python scripts/seed_context.py index
python scripts/seed_context.py search discovery
python scripts/check_mcp.py
python scripts/seed_context.py config --client claude
```

Merge the printed server entry into `.mcp.json`, preserving other servers. It contains
machine-local absolute paths, not secrets; do not commit it. Start Claude and approve the
reviewed server via `/mcp`. Make real calls before marking it connected. See the
[MCP guide](docs/integrations/mcp.md) for precise commands and other clients.
Reindex after source changes; stale results are rejected rather than presented as fresh.

## Resolve long-running uncertainty without adding bureaucracy

Use [decision planning](docs/workflows/decision-planning.md) only when questions span
sessions or depend on other questions. Clear, already-authorized changes skip it. A
map distinguishes precise blockers, fog and exclusions; it never grants execution rights.
The [approval guide](docs/workflows/approval-binding.md) binds actual scope approval to
specific files and decisions. Existing users must follow the [upgrade instructions](docs/upgrading.md).

## Run the evaluation and governance examples

[Benchmark demo](docs/workflows/benchmarking.md) compares a rule-based extractor with a
known-bad baseline. It does not call or rank real models. It intentionally rejects promotion
on synthetic examples. [Governance examples](docs/workflows/governance.md) exercise real
schemas and local preflight, without authorizing external actions or reading secrets.

## Green means what was actually checked

Before initialization, CI validates this starter and requires the MCP protocol job.
After initialization, `seed_ci.py --profile` retains starter regressions **and** runs the
application checks; those begin unconfigured/BLOCKED. A separate scope job checks current
approval (or a protected documentation-only exception). Optional MCP is omitted only with
a recorded reason. Opted-in feature verification maps run automatically after successful application checks. All three job groups must succeed; missing/skipped required jobs fail.
No `echo`, `true`, deleting tests or changing an evaluator to manufacture green status.
UI work needs browser behavior checks on the actual app; a template cannot verify future UI.

## Public use and contribution

MIT licensing applies to original Seed Repo files; retain the notice. Dependencies keep
their own licenses. Book/third-party skill archives, private conversations, data and font
files are NOT redistributed. [NOTICE](NOTICE.md) records conceptual sources and boundaries.
Review dependencies and local permissions before running a downloaded repository.

Maintainers: do not initialize this checkout as an application. Follow the
[publishing checklist](docs/maintainers/publishing.md), run hosted tests, configure protections,
and review the final export before announcing a release. The archive has no Git history.

## Integration hardening and adoption

Read [the fixed-findings matrix](docs/integration-hardening.md) and
[upgrade steps](docs/upgrading.md) before integrating into an existing app. The release fixes
cross-component handoffs, not just individual functions. Use `doctor` to distinguish available,
applicable, current/stale evidence, and unverified integrations. Public exports use a reviewed
exact-file inventory and reject local client configuration. Hosted GitHub, installed clients,
and cloud authorization are still verified separately; this ZIP is not an attestation.
