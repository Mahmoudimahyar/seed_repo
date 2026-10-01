# Optional decision planning

Seed Repo 0.3.0-rc.1 adds a local decision lifecycle. It does not install Wayfinder,
OpenSpec, GSD, Beads or an external tracker. See [sources](../research/decision-planning-sources.md).

## When to use it

Use ordinary implementation for clear, authorized small work. Use discovery/research for
one bounded uncertainty. Use this planner when questions depend on other questions or must
survive multiple sessions. The default initializer creates NO planning map. Marketing,
sales, UI and paid services remain separate user choices.

The objects are deliberately distinct:

| Object | Meaning |
|---|---|
| Map | Destination, scope, constraints, exclusions and still-imprecise fog. |
| Ticket | A precise question, even if dependencies currently block its answer. |
| Resolution | Existing decision-schema record containing answer, authority and evidence. |
| Task | Executable work after the required decisions and build approval are settled. |

The map is an index, not a second specification. Proposed changes do not rewrite accepted
behavior until reviewed. Use [change proposals](../../templates/change-proposal.md) and
[plan review](../../templates/plan-review.md) only when needed.

## Storage and privacy

`.seed-local/decisions.sqlite` is the ONE authoritative local backend. Python's SQLite is
used in-process; no server, embedding model, hosted tracker or paid API is required.
Transactions serialize writes on one local filesystem. A claim has a random token, unique
run owner and expiry; default map capacity is one. Revision compare-and-set prevents blind
updates. Claims do not grant tool permissions. This is not a distributed lock or sandbox.
Do not put the database on a multi-machine/network-filesystem write path.

Read-only snapshots are portable handoffs/backups, not a second live backend. Export keeps
history and source fingerprints but excludes claims and local selection. Import only into
a map ID absent from the destination; missing/changed evidence is stale. Snapshots are
untrusted, unsigned records, not authenticated approvals. Review ownership and actual
consent after transfer. Do not commit private runtime state, transcripts or claim files.
Before changing machine/checkout, export the map and preserve the referenced approved
sources privately. The starter ZIP intentionally contains none of a user's live state.

## Try the synthetic example

These commands only create a toy planning map. They do not build an application or create
an approved answer. Run from the repository root after installing requirements-dev.txt.

```bash
python scripts/seed_plan.py create --file examples/planning/map.json
python scripts/seed_plan.py create --file examples/planning/map.json --write
python scripts/seed_plan.py add --map demo-organizer --file examples/planning/privacy.json --write
python scripts/seed_plan.py add --map demo-organizer --file examples/planning/parser.json --write
python scripts/seed_plan.py handoff --map demo-organizer
python scripts/seed_plan.py get --map demo-organizer --ticket privacy
```

The privacy question awaits the named human; parser selection is a precise blocked question.
`required_evidence` names existing prerequisite source files. `evidence_requirements` states
what would settle the question; assessing sufficiency still needs judgment. The eventual
decision record may cite additional files created during research.

## Claim, resolve and recover

```bash
python scripts/seed_plan.py claim --map demo-organizer --ticket privacy --owner run-001 --expected-revision 1 --out .seed-local/claims/run-001.json --write
python scripts/seed_plan.py handoff --map demo-organizer --ticket privacy
python scripts/seed_plan.py release --map demo-organizer --ticket privacy --claim-file .seed-local/claims/run-001.json --write
```

Before a real `resolve`, create an authentic accepted/rejected record using the existing
[decision schema](../../schemas/decision.schema.json). For this integration, its
`workflow_id` is the ticket ID, and `scope` equals the exact map scope. Policy hash must
match `authority.policy_ref`. Human-required/interview decisions require the named owner's
recorded human approval; terminal exclusion or supersession also requires that human.
All evidence references must be safe, existing repository-relative files, not secret files,
URLs or hidden session transcripts. Record a local reviewed citation for a remote source.
No CLI produces human consent for you.

```bash
# Replace paths/IDs with the real record and live claim; this is not a runnable approval example.
python scripts/seed_plan.py resolve --map MAP --ticket QUESTION --record docs/project/decisions/answer.json --expected-revision REV --claim-file .seed-local/claims/RUN.json --write
```

Claim expiry can be renewed with `renew`; a second worker may claim after expiry, and the
old token no longer works. Stop blocks mutations except release. An emergency stop needs
no explanatory text. Do not overwrite a live claim file: use a new run/file name.

`get` reports the current ticket revision. `revise --file ... --expected-revision ...`
reopens a question while retaining prior records. `revise-map` changes the map revision.
Resolve with `--terminal out-of-scope` or `--terminal superseded --replacement ID` when
appropriate; neither outcome counts as ordinary prerequisite success.

## Status and staleness

Stored states are open, awaiting-human, resolved, out-of-scope and superseded. The current
view derives exploring, blocked and stale. A dependency must currently be resolved AND
have an explicitly allowed outcome (accepted or rejected). Closed is not synonymous with
satisfied. Missing references and cycles are rejected.

Resolution snapshots bind the map revision, direct prerequisite signatures (which include
their transitive dependencies), policy, evidence and answer bytes. Changes mark affected
answers stale on the next read; downstream resolved answers become stale and unresolved
questions remain blocked. No answers are silently edited. Adding unrelated tickets or
updating claims does not invalidate an independent resolved decision. Revising the map is
conservative: every answer in that map needs re-evaluation. Reverting only an evidence
file to identical bytes restores that file's old fingerprint; creating a new decision/map
revision does not. Expired scoped decisions remain stale even without file changes.

## Choose the correct effort and produce a bounded handoff

```bash
python scripts/seed_plan.py select --map demo-organizer --write
python scripts/seed_plan.py handoff --ticket privacy --limit 4
python scripts/seed_plan.py history --map demo-organizer --ticket privacy --limit 8
python scripts/seed_plan.py export --map demo-organizer --out .seed-local/exports/demo-001.json
```

With several maps and no selection, handoff refuses to guess. Selection is only a local
hint; parallel sessions must always specify `--map`. Handoffs return bounded records and
source pointers, not full files, transcripts or claim tokens. `truncated` warns of omitted
items; retrieve the map/ticket before acting if necessary. Priority is a declared rationale
and simple deterministic ordering, not a model's fabricated probability.

An export can be imported elsewhere with `import-snapshot --file ... --write`, never over
an existing map. This is not live synchronization. [Tracker adapters](planning-backends.md)
remain an explicit future integration, not a hidden GitHub/Beads write path.

## Approve implementation

Select only the required decision roots and accepted outcomes in readiness's `planning`
list. Their dependency closure is checked automatically. The [approval binding](approval-binding.md)
then covers those decisions plus the exact scoped specification. Other unrelated open
questions do not block that approved slice. A planning resolution, successful probe, or
schema-valid record alone never authorizes application implementation.

## Execution boundary

Resolvers describe how evidence should be obtained. This CLI never executes a resolver,
calls a model/API/browser, spends its declared budget or grants credentials. Prototype and
prerequisite tickets require a valid workflow-contract reference before they are eligible.
Use the existing governance preflight, trusted executor, OS isolation and actual approval
for any real operation. Numerical limits here are planning constraints and lease bounds;
external time/spending controls belong to the executor, not the map.

## Portable approval consumer (0.3.1)

An approval may reference a reviewed sanitized map snapshot so fresh CI can recheck the same
decisions without carrying `.seed-local/decisions.sqlite`. The snapshot is hashed into approval
and checked against current evidence; a live local map must agree. See
[approval binding](approval-binding.md). This temporary CI view is not a second live backend,
restored authority, synchronized tracker, or runtime spending budget.
