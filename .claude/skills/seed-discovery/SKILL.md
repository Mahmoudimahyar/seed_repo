---
name: seed-discovery
description: Interview a new project owner, resolve scope and gaps, and prepare buildable docs before application coding. Do not trigger for an already scoped routine fix.
---

# Discovery

## Understand
Read AGENTS.md, START_HERE.md, seed.json and supplied project material first. Separate
maintaining the starter from creating a new application. Infer only what the evidence
supports. Identify mode and independently confirm UI, marketing, sales, and AI scope.
Ask a few missing high-impact questions with recommendations, not an exhaustive survey.

## Specify
Preview initialization through scripts/seed.py, then apply only after scope is clear and
approved. Follow docs/workflows/discovery.md. Research consequential choices using current
primary sources and existing implementations. Fill only relevant docs/project files.
Define contracts, states, failures, permissions, dependencies, observable acceptance and
test mapping. UI needs a global map and detailed feature flows; CLI/API needs equivalent
command/contract flows. Track unresolved blockers and explicit exclusions.

## Obtain approval
Show the active-scope specification and implementation/test plan. Record actual user
approval; never invent it. Check readiness using the provided command, recognizing that
it validates recorded fields, not semantics or identity. Do not write application code
until scope is approved. Authorized isolated feasibility experiments are separate tasks.

## Tacit knowledge and decision integrity
Ask for normal cases, exceptions, recurring decisions, operating dependencies, friction
and expert judgment. Separate historical workarounds from approved future rules. Write
rejection scenarios for privacy and scope constraints. Do not impose a corporate mission,
mandatory marketing, headcount targets or enterprise data platforms on a simple tool.

## Planning scale and proposed versus accepted behavior
For a clear authorized small task, avoid another discovery ceremony. For a bounded unknown,
resolve it directly. For multi-session uncertainty, use seed-wayfind and its exact map ID.
Separate in-scope fog, precise blockers and excluded scope. Challenge the premise and seek
an existing solution first. Distinguish current accepted behavior from proposed deltas.
Use a shared glossary and normal/exception examples; examine invariants across features.
Generate a proposal fingerprint only when recorded scope evidence is ready. The real user
approves that fingerprint; record existing approval without creating it. See
`docs/workflows/approval-binding.md`. A planning note cannot override approval requirements.

## Integration contract

Register active feature packets with seed.py register-feature and read docs/workflows/feature-registration.md. All active feature docs belong to the approval; a global PRD does not implicitly bind an unregistered flow. Record optional MCP applicability; never create irrelevant features just to fill a template.

## Existing code and behavioral contracts
For legacy adoption, distinguish observed behavior, documented promises, inferred intent,
and approved intended behavior. Characterize risky existing boundaries before changing them;
do not ratify a bug as a requirement. Use concise preconditions, results, failures and
counterexamples for ambiguity. Internal design suggestions are not binding scope by default.
