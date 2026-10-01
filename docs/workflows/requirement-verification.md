# Optional requirement-to-executed-test traceability

This small pilot links existing feature requirements to ordinary JUnit test output. It does
not generate tests, select a new test framework, call a model, authenticate approval, or prove
semantic coverage. It is NOT enabled merely by using Seed Repo. A tiny project can use the
approved global specification plus its ordinary tests.

## Enable for one active feature

Register the feature using [feature registration](feature-registration.md). In its requirements.md,
declare stable headings such as `## REQ-export-001: Preserve the existing file`. IDs are scoped to
the feature slug. Fenced examples do not declare rules. Old prose/table formats continue working
without a verification map; the pilot requires the explicit heading convention.

Copy the optional templates/verification-map.json to that feature root as verification.json,
then replace the example. It must map exactly the set of declared IDs, without duplicating the
normative descriptions. The approved test plan should reference this map, not maintain another
set of executable IDs. All files in the active root, including the map, are approval-bound.

Each requirement selects automated, manual, or post_release and records why. Automated rules
need one or more exact test IDs. A test may support several rules. Manual checks remain NOT_RUN
and BLOCKED in this automated pilot: use the separately reviewed manual acceptance process,
not fabricated machine evidence. Post-release observations are reported as OBSERVE_LATER,
never as tests that passed; all-post-release maps return NOT_APPLICABLE, not PASS.

## Test command

The command is a shell-free argv array with a timeout. It must use `{junit}` for its fresh
JUnit output path. `{python}` expands to the current interpreter. For a pytest application,
use its actual configured environment, for example:

```json
{
  "argv": ["{python}", "-m", "pytest", "tests/test_export.py", "--junitxml={junit}"],
  "cwd": ".",
  "timeout_seconds": 120
}
```

pytest is an example application dependency, NOT installed by the starter. Other runners can
write the supported JUnit subset through their own reporters. Case IDs are the exact
`classname::name` pair; when classname is empty, use name alone. Inspect the actual XML, do not
guess from filenames. No wildcard, model-based or fuzzy match is used. No runner is installed
implicitly and no imported old XML can stand in for execution.

```bash
python scripts/seed_trace.py plan --feature export
# After ordinary authorization for trusted local tests:
python scripts/seed_trace.py run --feature export
python scripts/seed_trace.py check --report .seed-local/verification/RUN_ID/report.json
```

Replace RUN_ID with the actual returned ID. `plan` does structural checking before executable
tests necessarily exist. `run` creates a unique local output directory, uses the shared bounded
process runner, captures raw output privately, and compares source fingerprints before/after.
A configured command executes with the caller's environment/privileges. This is a verification
tool, not a new permission grant or governed production executor. Use isolated environments for
untrusted tests and protect test commands/requirements from self-certification.

## Consumer: application CI

`seed_ci.py --profile` runs retained starter checks, real application checks, and then all active
feature verification maps. If earlier checks fail, maps are NOT_RUN. If no feature opts in,
traceability is NOT_CONFIGURED and ordinary CI retains its existing meaning. A bare `seed_ci.py`
without --profile is deliberately only the selected command checks; it does not claim full
integration. Do not nest seed_ci or seed_trace inside a map's own command.

Mapped missing or skipped tests block acceptance. Any reported test failure/error, including
unmapped supporting tests, fails the run. Nonzero command exit cannot be overridden by passing
XML. A missing/empty/ambiguous report blocks; changed source makes the evidence STALE. Output
and XML are bounded. A STOP file blocks before execution. `check` rechecks local envelope/XML
integrity and source freshness; these hashes are not signatures or trustworthy against a
malicious writer who can rewrite both the evidence and its checksums.

The pilot supports UTF-8 testsuite/testsuites with exact testcase identities and failure/error/
skipped outcomes, plus ordinary output/properties. It rejects DTD/entities, duplicate case IDs,
unsupported retry extensions, count mismatches and ambiguous statuses. Adapt and test a new
report format explicitly rather than silently dropping information. One feature command has
one fresh JUnit report; combine/shard through a reviewed runner adapter if needed.

`doctor` reports configured plans, not semantic coverage. Current detailed evidence is in the
technical report's requirement_traceability entry, which retains the case mapping, process
result and hashes so CI does not upload dangling references alone. Full raw logs/XML remain
local by default; they may contain sensitive application data. Review even summaries before
publishing them to a broader audience. The original artifacts are needed for independent
checksum rechecking, and are not made public automatically.

## What remains human or independent review

Check the assertions really test the rule, review counterexamples, require the applicable
manual/browser/security/integration acceptance and authenticate reviewers outside local files.
A useful mapping reduces forgotten tests; it does not prove requirements are complete. The
candidate has unit/fixture tests and a real local pytest example, but no cross-framework
certification or controlled native-agent performance experiment.
