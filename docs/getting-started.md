# Start your own project

## 1. Obtain an independent copy

On the published repository, use **Use this template → Create a new repository** and
include only the default branch. Pick your own repository name and visibility; private
can be appropriate even though Seed Repo is public. A template-created repository starts
its own history. Fork Seed Repo when contributing upstream instead.

ZIP users: extract into a new directory, then run commands from the folder containing
`seed.json`. Hidden directories such as `.agents`, `.claude`, and `.github` are required.
Do not copy the ZIP over an existing application. See [existing-repo adoption](maintainers/integrating-existing.md).

The official GitHub template instructions are linked in the [source register](research/sources.md).

## 2. Inspect, then run the local checks

Review repository instructions and scripts before granting a coding agent workspace
access. Install Python 3.11+ and Git separately. Your preferred agent also needs its own
installation and authentication. Basic initialization needs no API credentials or packages. Full governance/tests require
requirements-dev.txt; the optional MCP adapter additionally uses requirements-mcp.txt.
Create and activate a local virtual environment as shown in README.md before installing.

Linux, macOS, or WSL:

```bash
python3 --version
python3 scripts/seed.py doctor
python3 scripts/seed.py validate
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s scripts/tests -v
```

Windows PowerShell:

```powershell
py -3 --version
py -3 scripts/seed.py doctor
py -3 scripts/seed.py validate
py -3 -m pip install -r requirements-dev.txt
py -3 -m unittest discover -s scripts/tests -v
```

The doctor reports binary presence, not authentication or client compatibility. No
supported agent is installed or upgraded automatically. An unavailable client does not
prevent documentation work with a different capable client.

## 3. Begin the interview

Open the repository in your agent and paste the prompt in [START_HERE.md](../START_HERE.md).
Describe the outcome, users, constraints, and what is out of scope. Provide existing
material first. Store private raw documents locally under `private/`, not in public Git.
Review generated requirements for confidential information before committing them.

The agent should identify the mode and capabilities without repeating questions already
answered. It should not initialize every project as a SaaS or enable marketing by default.

## 4. Initialize only after scope is clear

Example: a CLI, no website, marketing, or sales.

```bash
python3 scripts/seed.py init --name my-tool --mode cli
python3 scripts/seed.py init --name my-tool --mode cli --write
```

The first command previews paths; the second applies them. For an application with a UI
and AI capability, explicitly use `--ui --ai`. `--marketing` and `--sales` are independent
opt-ins. Available modes are listed by `python3 scripts/seed.py init --help`.

Initialization creates project documents/readiness records, updates `seed.json`, and
replaces `quality/seed-checks.json` with unconfigured application checks. The known starter
checks remain in `quality/template-checks.json`. It does not install packages, write
application code, change remotes, create a repository, or populate `.env`.

It refuses an already initialized project, known file conflicts, symlinked targets, and
a customized active CI configuration. Writes are preflighted but are not a multi-file
crash-atomic transaction. Commit or back up a working tree before initialization; inspect
a partial result rather than rerunning blindly after an interrupted disk write.

## 5. Complete and approve the build scope

Fill the generated PRD, architecture, contracts/flows, test strategy, configuration plan,
and dependency decisions through the [discovery process](workflows/discovery.md). Add
feature packets only when relevant. The user—not the agent pretending to be the user—
approves the exact scope and evidence revisions. Follow [approval binding](workflows/approval-binding.md)
to generate a proposed fingerprint and record actual approval without manufacturing consent.
For multi-session uncertainty, optionally use [decision planning](workflows/decision-planning.md).

```bash
python3 scripts/seed.py ready
```

An initial BLOCKED result is expected. READY only validates the recorded fields/files;
it does not prove the product is correctly specified or authenticate the approver.

## 6. Implement and verify

After approval, wire the actual stack's setup, checks, integration services, build, and
applicable browser/evaluation commands into `quality/seed-checks.json`. Python invocations
can use `{python}` to select the runner's current interpreter. Mark non-applicability with
an actual scope decision; do not bypass missing checks with success-only commands.

```bash
python3 scripts/seed_ci.py
```

The runner executes repository-controlled commands, not a secure sandbox. Run in a safe
environment. Review logs before sharing; configured tools may emit sensitive data.
Use [implementation](workflows/implementation.md) and [GitHub delivery](engineering/github-operating-model.md).

As the app takes shape, replace the root README with its own setup/use instructions while
retaining relevant Seed Repo attribution/license notices and the selected workflow docs.
