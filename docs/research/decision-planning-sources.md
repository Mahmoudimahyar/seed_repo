# Decision-planning provenance and design choices

Implemented from the supplied Seed Repo Wayfinder review (2026-09-20), after inspecting
0.2.0-rc.1 source and reproducing its 155-test baseline. The review was the design input;
this implementation does not claim a new independent web survey or live-agent comparison.
Upstream material is referenced, not installed, executed or copied into a combined plugin.

| Reference | Adopted component | Deliberately not adopted |
|---|---|---|
| Wayfinder | Decision tickets, fog/blocker separation, index-like handoff | Agent-writable permission exceptions, heavyweight default workflow |
| Superpowers | Scale-aware clear/bounded/probe/multi-session paths | Ceremony before every change |
| OpenSpec | Proposed deltas distinct from accepted baseline | Competing specification authority |
| GitHub Spec Kit | Structural and semantic review kept separate | LLM checklist as proof |
| GSD | Backward outcome-to-task review and scoped handoff | Mandatory worker fleets |
| Planning with Files | Explicit effort identity for recovery | Per-tool narration and duplicate mutable plans |
| BMAD | Shared domain/role invariants across features | Mandatory business departments |
| Beads | Outcome-aware dependency and claim concepts | Mandatory service or claims of distributed locking |
| GStack | Premise challenge and reuse/do-nothing options | Browser-first research or runtime markers as authorization |
| Domain modeling/prototyping | Shared vocabulary and isolated feasibility evidence | Automatic prototype promotion |

Primary references as recorded in the review:
- [Wayfinder article](https://www.latent.space/p/wayfinder-skill)
- [Article-linked Wayfinder source](https://github.com/mattpocock/skills/blob/9c9f36ccd3995266cd675468af71639c8dde1ec5/skills/engineering/wayfinder/SKILL.md)
- [Superpowers brainstorming](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md)
- [OpenSpec concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md)
- [Spec Kit](https://github.com/github/spec-kit)
- [GSD](https://github.com/open-gsd/gsd-core)
- [Planning with Files](https://github.com/OthmanAdi/planning-with-files)
- [BMAD planning](https://docs.bmad-method.org/plan/choose-a-planning-path/)
- [Beads](https://github.com/steveyegge/beads)
- [GStack office hours](https://github.com/garrytan/gstack/blob/main/office-hours/SKILL.md)

The local implementation uses the existing JSON Schema dependency and Python's SQLite;
no new network service or probabilistic routing layer is required. Later tracker adapters
must undergo their own authorization, license, API and concurrency review. Published
upstream names or popularity do not establish correctness or suitability.

Model-behavior evaluation scenarios are in evals/wayfinding. They have NOT been run against
live coding agents. Deterministic tests exercise bookkeeping, state changes and failure
paths; they do not prove interviews improve or that a model obeys the new skills.
