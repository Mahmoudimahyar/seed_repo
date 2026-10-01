---
name: seed-simplify
description: Review recently changed code for unnecessary complexity after behavior checks pass, preserving behavior and safety. Not a repository-wide rewrite.
---

# Simplify changed code

## Check necessity
Compare the diff with approved requirements and the repo's canonical examples. Challenge
pass-through wrappers, premature factories, speculative flags/fallbacks, repeated business
rules, unused exports, unnecessary state, and unrelated file changes. Ask what requirement
makes each new layer necessary.

## Improve clarity
Prefer readable direct control flow, descriptive domain names, and narrow public contracts.
Reuse approved standard/library features. Remove obsolete code rather than commenting it
out. Do not equate fewer characters with clarity. Do not penalize generated clients or
useful tests by applying a handwritten-production line-count target.

## Preserve and verify
Preserve authorization, validation, concurrency guarantees, accessibility, error visibility,
observability, and compatibility. Rerun behavior checks after simplification. Report
necessary complexity and why it remains. Do not reformat or refactor unrelated code.

## Existing capability, not copied internals
When a wrapper duplicates a library/SDK feature, verify that feature in the actual installed
public interface before removing our code. Optional source/Graphify evidence can guide the
investigation but is not runtime proof. Keep necessary contract checks and error behavior;
do not reduce line count by relying on private functions or unverified source versions.
