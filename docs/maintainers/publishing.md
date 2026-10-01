# Publish Seed Repo 0.5.0-rc.1

This is the maintainer path for distributing the **uninitialized public template**. People
building applications should follow [START_HERE](../../START_HERE.md) in their own copy.
These instructions prepare/upload the reviewed files; no supplied script creates a GitHub
repository, publishes a release, modifies remote permissions, or deploys anything.

## 1. Review the candidate and destination

Extract the release into a new directory and work in its `seed-repo` folder (the one containing
README.md). Do not run `seed.py init` in the publishing checkout. Confirm LICENSE/NOTICE rights
and the chosen MIT license, review hidden files, and keep the external-source registry empty.
The archive contains no Git history, private intake, model weights, fonts, upstream skill
bundles, caches, credentials, or local MCP configuration. Run an independent approved secret
scanner on the final staged tree and any imported history; the starter's pattern checks are
limited, not a security audit.

For an existing remote, **do not** rerun `git init`, create another repo, force push, or overwrite
history. Integrate the reviewed changes on a normal branch and PR under its existing protections.
The commands below are for a new, explicitly approved public repository only. The repository
name/account, public visibility and license remain maintainer decisions.

## 2. Verify locally before publication

Python 3.11+ and Git are prerequisites. Install dependencies in an isolated environment with
network access. Examples below use Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/seed.py doctor
python scripts/seed.py validate --public
python scripts/seed_ci.py --profile
```

On Windows PowerShell, create the environment with `py -3 -m venv .venv`, then use
`.venv\Scripts\python.exe` instead of `python` for the remaining commands. Activation is
optional; no execution-policy weakening is required.

The upstream template ships an optional MCP adapter, so its maintainer CI requires the real
protocol check. Verify on a connected machine:

```bash
python -m pip install -r requirements-mcp.txt
python scripts/seed_context.py index
python scripts/check_mcp.py
```

Do not suppress a failed or blocked check to create a green release. External opensrc/Graphify
providers remain separately optional; use [their acceptance guide](../workflows/external-source-research.md)
before advertising installed-provider compatibility. Read [validation](../validation.md) for
what ran locally and what remains unverified; a candidate download is not a hosted attestation.

## 3. Commit a fresh, inspected checkout

First inspect the directory, then initialize this new checkout only:

```bash
git init -b main
git status --short
git add --dry-run .
```

Review the complete list. Generated/private local paths must not be staged. Then:

```bash
git add .
git diff --cached --stat
git diff --cached
git commit -m "feat: prepare Seed Repo 0.5.0 release candidate"
```

Do not add client configuration to Git just to make MCP work on another machine. Adopters use
the configuration generator to produce their own paths. Do not remove untracked personal work
from an existing checkout merely to satisfy public validation; publish from a clean export.

## 4. Create the public GitHub repository

Install GitHub CLI separately. Check that the authenticated account is the intended owner:

```bash
gh auth login
gh auth status
```

**The next command makes the committed files public.** With `seed-repo` alone, GitHub CLI uses
the authenticated account. For an organization, replace it with `YOUR_ORG/seed-repo`:

```bash
gh repo create seed-repo --public --source=. --remote=origin --push
gh repo edit --template --description "A research-first starter for human and AI-assisted software development"
```

Do not change an existing private repository's visibility as a substitute for this procedure.
For the browser route, create an **empty** public repository (no generated README/license/
.gitignore), use its push instructions, then enable **Settings → General → Template repository**.
Upload through Git so hidden `.agents`, `.claude`, `.github`, `.seed`, and `.cursor` files are
retained. Do not upload only the ZIP or use a picker that omits those directories.

## 5. Activate and actually test the hosted controls

Set `main` as the default branch; prefer squash merge with the reviewed PR title; configure
working-branch deletion and an appropriate review policy. Run `gh run list --limit 10` or view
the Actions tab; inspect each run, including the optional-provider limits. Protect the actual
final check **seed-ci-required** only after confirming its check identity and reporting path.

Review `.github/rulesets/` (disabled examples) and create real CODEOWNERS from the example.
Ruleset files are not activated by uploading them. A lone author cannot independently approve
their own PR: add a reviewer or document a temporary solo policy rather than inventing one.
Protect workflows, evaluators, mappings, permissions and approval evidence from self-approval.
Check plan/repository-visibility support before promising merge queues or deployment reviewers.
No production credentials or deployment workflow are required to distribute this starter.

Enable and test private vulnerability reporting, appropriate scanning/push protection, and a
working support/moderation process. Update project About/topics without unverified status badges.
Rehearse a deliberate failing PR in a sandbox and confirm it cannot merge under the intended
policy. Test a template-generated downstream copy and a ZIP-based copy. New copies do not
inherit every server-side permission, ruleset, secret, environment or repository setting.

## 6. Build the clean release archive and verify it after extraction

From the final reviewed maintainer source:

```bash
python scripts/package_release.py --out .seed-local/releases
```

The exporter uses quality/export-policy.json, not Git's ignore file as its permission model.
It refuses unexpected distribution files, local configuration, archives, symlinks and fonts,
and refuses to overwrite an existing output version. It generates a manifest and ZIP checksum.
Extract into a different directory, install reviewed dependencies and repeat public validation,
technical CI and the protocol check. Verify the checksum and every manifest entry. Hashes prove
byte consistency, not author identity or security. Keep external verification evidence available
for reviewers and do not embed private raw test logs in a public release.

## 7. Draft, review, then publish the prerelease

After the preceding checks pass, tag the approved clean commit; use the established signing
policy when available. Never move or reuse a published version. If a candidate changes, assign
a new candidate version consistently in VERSION, seed.json, changelog and release notes.

```bash
git tag -a v0.5.0-rc.1 -m "Seed Repo 0.5.0-rc.1"
git push origin v0.5.0-rc.1
gh release create v0.5.0-rc.1 --verify-tag --prerelease --draft --title "Seed Repo 0.5.0-rc.1" --notes-file docs/releases/0.5.0-rc.1.md
```

Attach the verified ZIP/checksum to the **draft** (not an already immutable published release):

```bash
gh release upload v0.5.0-rc.1 .seed-local/releases/seed-repo-0.5.0-rc.1.zip .seed-local/releases/seed-repo-0.5.0-rc.1.zip.sha256
```

Review assets, notes and evidence on GitHub, then deliberately publish the draft. GitHub's
own source archives are also available, but their checksums are not the checksum of this
explicitly packaged ZIP. Immutable releases should receive every asset before publication.
Download once more and inspect that instructions and hidden files remain intact. Do not call
the candidate stable v1.0 or advertise guaranteed token savings before appropriate evidence.

## Primary references checked 2026-09-30

- [Create repository CLI](https://cli.github.com/manual/gh_repo_create)
- [Edit repository/template CLI](https://cli.github.com/manual/gh_repo_edit)
- [Create release CLI](https://cli.github.com/manual/gh_release_create)
- [Manage releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
- [Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use)

The retained action tag identities were rechecked with the official GitHub API. Hosted jobs,
remote settings, installed clients, public publication and external provider runtime execution
were not performed by preparing this archive.
