# Contributing to Seed Repo

Thank you for helping improve the starter. Fork this repository to contribute; use the
template button for a separate product. Discuss consequential changes in an issue before
building a large solution. A new prompt or skill should solve a demonstrated failure,
not duplicate an existing workflow.

## Local setup

Use Python 3.11+ and Git. Install `requirements-dev.txt` for the full tooling/test suite;
install `requirements-mcp.txt` to exercise the official protocol. No paid API key is needed
for the local synthetic tests. Run from the root:

```bash
python3 scripts/seed.py doctor
python3 scripts/seed.py validate
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s scripts/tests -v
python3 scripts/seed_ci.py
```

Use `py -3` on Windows. Do not run project initialization in the upstream maintainer
checkout. Test initialization in a disposable copy.

## Changes and review

Use a short-lived branch such as `fix/123-safe-init` or `docs/124-quickstart`.
Commit coherent checkpoints, inspect the staged diff, and stage explicit files/hunks.
No blind bulk staging of unrelated user work, direct protected-main pushes, or shared
history rewriting. Use a Conventional Commit PR title such as `fix(init): preserve user
files`. Mark breaking public behavior explicitly and describe migration steps.

Complete the PR template. Include reproduction and actual commands/results; mark checks
that could not run. Test fresh-template and initialized-project behavior. Do not change a
test/evaluator merely to manufacture a pass. For workflow, permissions, licensing, or
release changes, request appropriate maintainer review. Independent review must not be
forged through a bot identity or a second account.

Canonical skills live in `.agents/skills`. Update them there, then run:

```bash
python3 scripts/seed.py sync-skills --write
python3 scripts/seed.py validate
```

The sync command refuses to overwrite manually changed mirrors. Review the conflict,
then deliberately reconcile source and mirror; never discard edits automatically.

## AI-assisted contributions

AI help is welcome. The contributor remains accountable for correctness, licensing,
privacy, provenance, and review. Include material agent/model configuration when useful
for reproducing a workflow change. Never upload credentials, private prompts, client data,
raw session logs, or hidden evaluation datasets in a public PR. Do not claim model-quality
improvements without appropriate comparisons.

## Releases and conduct

See [maintainer publishing](docs/maintainers/publishing.md) and [release policy](docs/engineering/releases.md).
Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Contributions are intended to be
licensed under this repository's license; do not submit code you lack the right to share.

## Integration and distribution review

For behavior changes, test the handoff as well as each function: adapter → envelope → scorer,
feature registry → approval → executor, canonical skill → retired client mirror, and public
validation → ZIP → extracted files. Do not weaken an assertion to accommodate a broken handoff.

`sync-skills` previews retirement of known unchanged generated mirrors. Edited or orphaned
mirrors block synchronization for explicit reconciliation. No automatic deletion of user edits.

`quality/export-policy.json` is the maintainer-reviewed exact distribution inventory. A new
source/doc/test must be reviewed and explicitly added there; an unintended extra file must be
removed from the publish checkout. Never add machine-local configurations to the inventory.
The public validator and packager both enforce it. Do not regenerate it from an unreviewed
used checkout. Run final tests after extraction; retain upstream regression checks in adopters.
