# Document templates

Copy only relevant documents. The initializer creates the core project set and explicit
capability-specific documents. `__FILL__` marks an unresolved section, not an accepted default.
No universal folder structure, auth system, or UI stack is selected here.

Feature templates are copied manually when a feature warrants them. API/data/UI files are
conditional; a simple tool need not create all of them. Relate requirement, flow, test,
source, and decision IDs rather than duplicating contracts in prose and generated specs.

Optional decision planning uses decision-map.json and decision-ticket.json. Replace all
synthetic example values, sources, owners and the unfilled identifier; do not create maps
for routine clear changes. change-proposal.md separates proposed behavior from the accepted
baseline. plan-review.md separates structural checks, semantic review and actual approval.

## External-source evidence (optional)
`external-source-request.json` is a schema-validated request, not a fetched dependency or license
approval. `source-mapping-review.md` records actual evidence linking the snapshot, package artifact,
public-interface test and reuse decision. Fill intentionally; do not instantiate every template.
Machine-specific tool paths and copied repositories stay in `.seed-local`, not these documents.

## Optional executable verification
`verification-map.json` is an example for a deliberately registered feature; do not instantiate
it automatically. Replace its IDs and actual runner command and place it as verification.json
in that active feature root. See docs/workflows/requirement-verification.md. Test plans remain
stable input; execution results go elsewhere. Existing plain specifications need no migration.
