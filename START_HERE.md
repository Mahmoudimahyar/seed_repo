# Start here

## Are you building a project, or maintaining this starter?
`seed.json` begins in template mode. A maintainer fixing Seed Repo must not initialize it.
A new user should open their template-generated copy in the chosen coding agent and use
[the README prompt](README.md). Only relevant skills and documentation should be loaded.

## Discover before implementing
Read provided documents first. Resolve the user's actual outcome, workflows and exceptions,
constraints, non-goals, data, permissions, cost tolerance and testable acceptance criteria.
Ask a few high-impact questions per round; do not re-ask settled questions. Research
consequential/uncertain/current choices from dated primary sources and reputable maintained
implementations. Explain the stable baseline, frontier alternative and actual recommendation.
Stop researching once the decision is sufficiently supported; revisit on a relevant trigger.

## Initialize only after agreeing scope
Preview an example CLI project (no marketing/sales/UI/AI inferred):

```bash
python3 scripts/seed.py init --name my-tool --mode cli
```

After the user approves the proposed files, repeat with `--write`. Flags `--ui`,
`--marketing`, `--sales`, and `--ai` are independent opt-ins. An AI system should explicitly
select --ai; a product is not automatically a marketing project. Consult `init --help`.
Templates contain placeholders on purpose. Fill generated docs/project files, feature
packets, exact test mapping, and real configuration needs. Put raw intake in private/,
not the public repository. Never paste secrets into chat or index them.

## Approve and build
Show the buildable active scope, architecture, contracts, UI map/flows when relevant,
test plan, open gaps and allowed actions. Follow the
[revision-bound approval workflow](docs/workflows/approval-binding.md): generate a proposal,
obtain actual approval of its fingerprint, then record that existing evidence. Run:

```bash
python3 scripts/seed.py ready
```

READY checks recorded fields, not human identity or specification correctness. Resolve
blocking gaps. Approved isolated feasibility experiments can occur earlier without being
misrepresented as the finished app. Continue through approved vertical slices with TDD,
reuse, simplification, applicable browser checks, reviewed PRs and verified completion.
All application checks begin BLOCKED until genuinely configured.

Use [local context](docs/integrations/mcp.md) when useful; do not spend context on an entire
repo read. Use [recovery](docs/workflows/execution.md) after interruptions. See
[requirements coverage](docs/requirements-coverage.md) for what is included and what still
requires project-specific credentials, services, evaluation or human authorization.

For multi-session uncertainty, use the optional [decision planner](docs/workflows/decision-planning.md)
and `seed-wayfind`. Clear authorized small work skips it. Choose the exact active map on
recovery. `seed-plan-review` checks a substantial plan's outcome coverage and cross-feature
invariants, but a model's review is not an authenticated approval or proof of correctness.

## Register actual feature packets and optional integrations

Use [feature registration](docs/workflows/feature-registration.md) before approving an active
feature packet. Top-level docs alone do not bind an unregistered feature. Record optional
MCP applicability with `configure-mcp` before changing it; false means not needed, not broken.
`doctor` derives current scope/test/context evidence and distinguishes it from the old phase hint.
Technical test success and scope acceptance are separate checks; see
[CI profiles](docs/engineering/ci-cd.md).

## Specification verification without extra ceremony
Use [spec-anchored TDD](docs/workflows/specifications-and-tdd.md): scenario list, one failing
test, minimal passing implementation, refactor and reconcile. Keep progress/results outside
frozen plans. Optional [requirement mappings](docs/workflows/requirement-verification.md) help
high-value features connect intended rules to actual test results without a new SDD framework.
