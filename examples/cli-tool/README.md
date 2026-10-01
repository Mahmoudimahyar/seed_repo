# Fictional example: line-cleaner CLI

This is a worked specification example, not an executable product or benchmark result.
It demonstrates the expected level of detail without importing a SaaS business model.

## Approved scope in the example

A local CLI removes exactly duplicated nonblank lines from a UTF-8 text file, preserves
the first occurrence order, and writes to stdout. No network calls, LLM, database, website,
accounts, payments, marketing, or sales. The user owns the input files.

## Contracts and cases

| ID | Requirement | Observable test |
|---|---|---|
| REQ-001 | Preserve first occurrence of each distinct nonblank line. | `a\nb\na\n` yields `a\nb\n`. |
| REQ-002 | Remove blank lines, not whitespace inside nonblank lines. | An input with blank rows removes them but preserves ` a `. |
| REQ-003 | Report missing file on stderr with a nonzero exit. | Temp-path test asserts exit, safe message, and empty stdout. |
| REQ-004 | Never modify the source file. | Hash the source before/after invocation. |
| REQ-005 | Reject invalid UTF-8 clearly. | Invalid byte fixture fails with documented exit/error. |

## Design and reuse decision

Use Python's standard file handling and argument parsing. No LLM step is needed. A
memory-backed set meets this example's agreed input-size constraint; unbounded streaming
or fuzzy deduplication is out of scope and would require another decision.

## Validation

Pure function tests for ordering/filtering, temporary-file integration tests for UTF-8 and
non-destructive behavior, and subprocess CLI tests for stdout/stderr/exit codes. Browser
checks are not applicable and the reason is linked to this scope decision. Test the actual
entry point instead of mocking every file operation.

## Initialization example

```bash
python3 scripts/seed.py init --name line-cleaner --mode cli
```

This previews the documents. The starter must never infer `--marketing`, `--sales`, `--ui`,
or `--ai` from the fact that a developer could eventually sell the tool.
