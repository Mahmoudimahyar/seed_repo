# Bounded execution and session recovery

Prefer the installed agent client's supported goal/plan tools to a custom daemon. A
client's claimed completion is not test evidence. For stable procedures, reuse scripts.
The supplied `seed_tasks.py` is a SMALL LOCAL deterministic task sequencer, not an AI
worker scheduler. It does not launch Claude, allocate cloud workers, or merge branches.

## Task graph versus context graph
The task graph orders dependencies. Workflow state records planned/running/checkpoint/
failed/passed work. The repository context graph locates evidence. None requires a shared
enterprise graph database. One writer owns a branch/worktree; independent research can run
in parallel. Coordinate at contracts, shared state, merges and budget boundaries.

## Local sequencer
Review [the example](../../examples/tasks/README.md), then create a real task plan matching
`schemas/task-plan.schema.json`. Record actual approval in a separate evidence file.
Preview first; `--execute` runs the reviewed argv commands with the current privileges.
A lock prevents concurrent local runs. Per-task timeouts, per-run step limits, and bounded
retry counts prevent unlimited repetition. The source fingerprint must match the last
checkpoint and the exact plan digest must remain unchanged before resuming.

Logs/checkpoints live under `.seed-local/`, excluded from publication and retrieval.
Before/after integrity comparisons detect out-of-scope edits AFTER execution. This policy
is separate from retrieval exclusions and hashes regular source, configuration, locks, tests,
large/binary and private inputs without emitting their values. Fixed generated runtime/dependency trees
are excluded, but tracked source is restored to the integrity set even under build-like folders.
Tracked runtime checkpoint/log files are rejected to avoid self-hashing. Symlink/submodule
inputs need an explicitly reviewed integration rather than an unsupported silent pass; this is NOT whole-machine monitoring or a sandbox. Use OS isolation and scoped
credentials. POSIX process sessions (including ordinary descendants) are terminated on timeout,
stop, output overflow, and command completion. Deliberately escaped sessions require OS controls.
Windows uses taskkill /T while the leader exists; full process containment requires a Job Object
or container. Those platforms/services must be tested in their actual deployment environment.

Interrupted process: inspect `task-run.lock` and confirm no worker still runs before
removing a stale lock. Never blindly unlock a live writer. Review a changed plan/source,
archive old local state, and create a newly approved plan rather than forge fingerprints.
Stop with `python3 scripts/seed_governance.py stop`; record the reason afterward if needed.

## Resume prompt
Read AGENTS.md, seed.json, the current task and its evidence. Inspect git status and
recent diff without overwriting work. Check actual MCP freshness/connectivity if enabled.
Identify current stage, missing approvals, failed/not-run checks and necessary questions.
Do not re-ask settled questions or load all docs. Recover one actionable slice, run targeted
checks, record evidence, and continue within approved scope and budgets. Do not present
configuration presence or a remembered success as freshly verified behavior.

## Approved application revision (0.3+)
Task plans for initialized applications now require `readiness_sha256` matching the exact
active readiness binding and `scope` matching its approved scope. The runner checks before
and after each command. A dependency decision changed only in the ignored planner database
still invalidates readiness and blocks continuation. See [approval binding](approval-binding.md).
Template-maintenance tasks and standalone runner examples do not require an application gate.

## Bind governed tasks explicitly

Ordinary ungoverned commands remain usable and are reported `NOT_CONFIGURED`, never certified
as governed. Set `require_governance: true` on a plan to require a binding for every task.
For a governed task, add `governance` with:

- `workflow`: exact safe workflow JSON path and `workflow_sha256`: its byte hash.
- `reference_sha256`: the complete reference hashes returned by `seed_governance.py references`.
- `request`: the action-request contract, including `execution_sha256` computed over
  `seedlib.common.dump({"argv": task["argv"], "cwd": task["cwd"]})` with SHA-256.

`examples/governance` and the governed-execution tests show these mechanics using synthetic
fixtures. In real work, construct the declaration from reviewed effects and actual approval;
never copy synthetic consent. Preflight resolves/validates data, eval, recovery and optional
purpose references, verifies pins and exact argv/cwd, then checks the declared permissions and
remaining budget before running anything. Denial starts no command. Bound references and scope
are checked after execution too. Local plan counters reserve declared calls/cost before running;
failed attempts count, elapsed time is retained, and remaining time caps the next action.

These counters are not global or authenticated billing. They do not monitor undeclared network
requests or every file operation inside arbitrary code. A requester who controls the executor,
policy or state can bypass local checks: deploy a trusted gateway/OS boundary for real enforcement.
Claims in the decision planner are coordination leases, not runtime budgets or permission grants.

## Shared process contract

Tasks, CI and candidate adapters use the same bounded subprocess primitive. Arguments may repeat
and may include legitimate empty values; the executable cannot be empty. No implicit shell.
Captures are bounded while streaming; excessive output fails explicitly. Keep safe logs available
but never rely on unlimited capture or dump sensitive data. Adapters halt on an execution failure
instead of hiding it behind retries. An interrupted runner lock must still be reconciled manually.

## Optional external-source inputs
Plans can include `external_sources`, an array of current objects from `seed_oss.py bind`.
The runner verifies the manifest, snapshot bytes and reviewed mapping evidence before resumed
PASS results, before each step, and afterward. Its checkpoint retains those bindings; doctor
marks recorded execution stale when a used external input changes. No binding is required for
ordinary tasks that do not use external source. This is change detection, not prevention of
arbitrary shell reads/writes. See [external research](external-source-research.md).
