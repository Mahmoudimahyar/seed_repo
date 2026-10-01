# One authoritative planning backend

The delivered backend is local SQLite via Python's standard library. No remote tracker,
Beads server, GitHub issue write integration, OpenSpec sync or distributed lock is installed.

For a team already using a tracker, retain it as authority. Do not silently maintain local
and remote statuses in parallel. A future adapter must define map/ticket identity, outcome
mapping (closed != accepted), expected-revision writes, atomic claims and lease expiry,
current-source evidence, conflict behavior, access controls, publication policy and recovery.

Before integrating one, test the actual backend's concurrency semantics, including lost
leases, network partitions, revoked access and stale workers. Issue assignment alone is not
a lock. Do not infer distributed safety from the local SQLite tests.

Current interoperability is a portable explicit snapshot: export, securely transfer the
snapshot plus necessary evidence, import into an absent local map ID, revalidate. Import
restores no claims and does not auto-select a map. It rejects overwrite and keeps prior
history. It is unsigned data, not an authorization certificate or live sync feed.

Do not add another service for a single-user CLI merely because the starter can scale later.
