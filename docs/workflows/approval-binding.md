# Revision-bound scope approval

`readiness.json` now uses schema_version 2. This is a deliberate compatibility change:
schema-1 checkbox approval is BLOCKED until migrated and reapproved. It is not silently
accepted as a new revision-bound approval.

The binding fingerprints the exact project/mode/capabilities, scope, gate/evidence files,
blocking-gap list and selected decision snapshots. It excludes the approval text to avoid
a circular hash. The separate approval record pins that text's bytes and must mention the
proposal fingerprint. Hashes detect changes; they do not prove identity, competence,
semantic correctness or authorization by an external system.

## Review first, then record existing approval

Finish applicable scope documents, clear real blocking gaps and mark genuinely satisfied
gates. Keep `approval.approved` false until the real approver has reviewed the proposal.

```bash
python scripts/seed.py approval-manifest --out .seed-local/approval-proposal-001.json
```

Read that proposal and the referenced documents with the actual approver. Record the actual
approval in a separate local/sanitized project file that identifies the approver, exact
scope, proposal SHA-256, date and genuine conversation/issue reference. Do not fabricate this
file to pass a gate. Do not include private transcripts or credentials.

```bash
# Only after actual approval exists; these commands record it rather than creating it.
python scripts/seed.py record-approval --by APPROVER --evidence docs/project/approval.md --proposal .seed-local/approval-proposal-001.json
python scripts/seed.py record-approval --by APPROVER --evidence docs/project/approval.md --proposal .seed-local/approval-proposal-001.json --write
python scripts/seed.py ready
```

Preview is the default. A changed specification makes an old proposal unusable. Merely
recomputing a binding without new matching approval evidence cannot restore readiness.
No signing or identity provider is built in. Treat local approval files as recorded evidence
and use real GitHub/cloud/team permissions for independent enforcement.

## Include optional decision-map requirements

Keep `planning: []` for work not using the planner. Otherwise, add references like:

```json
"planning": [{
  "map_id": "organizer",
  "requirements": [{"ticket_id": "parser", "allowed_outcomes": ["accepted"]}]
}]
```

Required roots must be resolved with allowed outcomes and current source/policy/dependency
snapshots. Their full dependency closure is included. Unrelated questions may remain open.
Missing local planner state blocks readiness; restore a reviewed export and its sources,
then verify real authority rather than manufacturing a replacement database.

## Preserve the boundary while coding

Set the executable task plan's `readiness_sha256` to the approved proposal fingerprint and
use its exact `scope`. Initialized applications are checked before and after each command.
If a document or decision changes, the runner stops before subsequent commands. This does
not undo the command that just ran; it is not a sandbox or continuous revocation service.

Any byte change in pinned evidence is conservatively stale. This includes whitespace and
progress edits: record execution progress in `.seed-local` checkpoints or separate task
reports, NOT inside the approved specifications. Changes to behavior/contracts go through
review and new approval. Source edits outside evidence do not themselves require repeated
scope approval; their tests and source-aware execution checkpoints remain separate controls.

## Migrate from 0.2.0-rc.1

```bash
python scripts/seed.py migrate-readiness
python scripts/seed.py migrate-readiness --write
```

The first command previews. The second preserves `readiness.v1.archived.json`, changes the
schema to 2 and clears approval. It refuses to overwrite an existing archive. Preserve
project docs, resolve actual gaps, generate a proposal and obtain real reapproval. Template
maintainers do not initialize or migrate an application merely to update the starter.

## Active feature evidence and clean CI (0.3.1)

Approval now includes the feature registry, every active feature document, and the MCP
applicability record. See [feature registration](feature-registration.md). Introducing a feature,
editing its flow, deleting a doc, or changing applicability invalidates approval. Code/test path
mappings identify planned implementation but do not hash evolving implementation as a fixed spec.

For planner-dependent approvals that must work in a fresh CI checkout, add `snapshot` to each
planning entry, for example `"snapshot": "docs/project/decisions-export.json"`. Use a reviewed,
sanitary export from `seed_plan.py export`; include all referenced approved source/policy files.
The export itself becomes approval evidence. CI imports it into a temporary view, checks the
required decisions and source hashes, and never creates/overwrites the canonical local database.
When local state also exists, it must agree with the snapshot. A stale/missing export cannot
silently substitute for live state. Snapshots are still unsigned records, not proof of consent.

`seed_acceptance.py` reports scope acceptance separately from technical CI. Protected GitHub
review/identity is still required to trust the record. A narrow documentation-only CI exception
permits discovery changes, not application implementation. See [CI profiles](../engineering/ci-cd.md).

## Registered external research
Nonempty `.seed/external-sources.lock.json` and its recorded mapping-review evidence are included
in the proposed application approval binding. An empty/absent registry leaves existing evidence
unchanged. A clean CI checkout can validate tracked identities without downloading source;
a task that uses a source must restore/check its local bytes separately. Changes need genuine
review/reapproval, not adjusted hashes. Local mapping review is not an artifact attestation or
authentication. See [source research](external-source-research.md).
