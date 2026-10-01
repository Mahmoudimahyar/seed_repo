# Evaluate reuse investigation before changing defaults

These are **scenario definitions**, not results or a new model runner. Reuse the project's
existing evaluation harness and keep model/client/tool configuration, starting revision,
requirements, permissions and user answers fixed across conditions.

Compare (A) current source/documentation tools, (B) verified external source + exact search,
and (C) the identical source + Graphify. Separate acquisition cost from graph construction.
Use [scenarios](scenarios.json) and independently verify the resulting changes against the
actual dependency artifact/public API. A readable graph/report is not task success.

Record successful accepted changes, version/API mistakes, human corrections, regression
failures, all calls/context sizes, time, cold indexing cost, warm query cost, dependencies,
and maintained application complexity. Do not reward fewer tests or missing error handling.
Do not use raw-corpus size divided by query output as an engineering token-saving percentage.
Pin source/configuration and report uncertainty/repeated runs before enabling a default.
No candidate benchmark or claimed saving is shipped with this release.
