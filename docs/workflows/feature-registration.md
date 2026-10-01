# Register the active feature scope

`docs/project/features.json` is the canonical feature declaration consumed by readiness and
context indexing. Initialization creates an empty registry; it does not invent features.
For a tiny tool, the approved global specification/test plan may be enough. Do not add fake
feature folders just to satisfy a template.

For a feature packet, preview registration:

```bash
python scripts/seed.py register-feature --id login --owner project-owner --docs docs/features/login --ui --code src/auth.py --test tests/test_auth.py
```

Add `--write` after review. Repeat `--code` or `--test` for exact planned files; their paths
need not exist before implementation. No globs or network paths. `--ui` requires the project's
approved UI capability. This command registers scope; it does not create behavior or consent.

Fill `requirements.md`, `test-plan.md`, and (for UI) `ui-flow.md` in the feature root. Other
API/data/contract artifacts can live there when relevant. The entire active feature root is
bound to approval: editing, adding or deleting its files makes old approval stale. Test mappings
are required but are declarations, not coverage proof. Keep progress logs outside frozen specs.
Implementation/test source changes remain subject to integrity and technical checks, not
reapproval merely for adding the implementation previously approved.

Unregistered subdirectories under `docs/features/` or `docs/project/features/` block readiness
and context-index construction. Do not hide active specs in arbitrary unregistered locations.
Registry records may be explicitly deferred with a meaningful reason; their unfinished docs
do not activate a feature. Changing that scope decision itself requires new approval.

When code/tests exist, the context index derives `documents` and `tests` edges from this
registry. Add finer symbol/section references in `.seed/context-links.json` when useful.
These are declared relationships, never evidence that tests ran. See
[approval binding](approval-binding.md), [MCP](../integrations/mcp.md), and
[status](../status.md).

## Optional requirement-level mapping
See [JUnit traceability](requirement-verification.md). When an active feature enables
verification.json, structural lint runs during validation/approval and application-profile CI
executes it after successful application checks. IDs and references are checked mechanically;
assertion adequacy is reviewed separately. Do not store mutable outcome cells in test-plan.md.
