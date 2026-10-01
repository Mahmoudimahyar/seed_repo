# Primary-source register

Checked: **2026-09-20**. These sources ground installation/distribution guidance; they are
not benchmark evidence or a promise that every installed client behaves identically.
Refresh when a referenced interface or policy changes. Links are not vendored dependencies.

| Area | Official source | Relevance |
|---|---|---|
| GitHub templates | [Create a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository) | Admin setting; templates distribute files, not complete account configuration. |
| Template consumers | [Create from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) | Independent project versus upstream contribution fork. |
| Public community files | [Healthy contributions](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions) | README, license, contribution, conduct and support guidance. |
| Repository CLI | [gh repo create](https://cli.github.com/manual/gh_repo_create) and [gh repo edit](https://cli.github.com/manual/gh_repo_edit) | Publication and template-setting syntax. |
| Claude instructions | [Memory/instructions](https://code.claude.com/docs/en/memory) | CLAUDE.md imports and AGENTS.md discovery conditions. |
| Claude skills | [Skills](https://code.claude.com/docs/en/skills) | Repo-local SKILL.md conventions. |
| Claude MCP | [MCP setup](https://code.claude.com/docs/en/mcp) | Configuration scope versus connection/tool verification. |
| Codex skills | [Build skills](https://developers.openai.com/codex/skills) | Local .agents/skills discovery (redirects to current docs). |
| Cursor skills | [Skills](https://cursor.com/docs/skills) | Client-specific skill discovery. |
| License | [MIT](https://choosealicense.com/licenses/mit/) | Proposed permissive license and notice retention. |
| Vulnerability reports | [Private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository) | Must be configured by the maintainer. |
| Actions security | [Secure use](https://docs.github.com/en/actions/reference/security/secure-use) | Least privilege, untrusted input, action review. |

The pinned checkout/upload action tags were re-read through the official GitHub tag API;
references and SHAs are in quality/action-pins.json. Pins identify reviewed references,
not proof of action security. Hosted execution remains separately unverified.

Conceptual workflow influences (not bundled implementations):
[GStack](https://github.com/garrytan/gstack), [Superpowers](https://github.com/obra/superpowers),
[Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), and
[Agent Skills](https://agentskills.io/specification). This packaging pass did not repeat
all prior research or independently measure their effectiveness.

Optional evaluation infrastructure to research for a real project:
[Inspect AI](https://inspect.aisi.org.uk/) and [Promptfoo](https://www.promptfoo.dev/docs/intro/).
No evaluation service is installed, invoked, or claimed to work in this distribution.


## 0.2.0 implementation references — checked 2026-09-20
- [Claude Code MCP reference](https://code.claude.com/docs/en/mcp): project configuration,
  stdio argv separation and actual connection verification.
- [Codex MCP configuration](https://developers.openai.com/codex/mcp): trusted project and
  user configuration; a local server remains separate from the coding agent.
- [Official MCP SDK v1 documentation](https://py.sdk.modelcontextprotocol.io/v1/): the
  maintenance API used by this adapter. New major versions require migration tests.
- [MCP 1.28.1 metadata](https://pypi.org/pypi/mcp/1.28.1/json): selected pinned maintenance
  release, dependency metadata and upstream notices, not a full security audit.
- [jsonschema validation](https://python-jsonschema.readthedocs.io/en/stable/validate/):
  Draft 2020-12 validation and explicit format checker usage.
- [Agent Skills format](https://agentskills.io/specification): focused entry points with
  progressive disclosure. This release uses canonical files and generated client mirrors.
- [OpenExO live book](https://openexo.com/organizational-singularity): conceptual inspiration
  only; uploaded packages are not redistributed. See NOTICE and governance adaptations.

Research provenance is dated. Referenced online pages can change. Code, tests and actual
run reports—not links or claimed skill invocation—determine implementation evidence.

## 0.4.0 optional external implementation research

[Pinned source/API review](external-source-providers.md) documents opensrc and Graphify targets,
Git acquisition semantics and intentional boundaries. Standalone extraction is reused, not the
providers' entire agent workflows. Runtime checks and comparative outcomes are separately reported.
