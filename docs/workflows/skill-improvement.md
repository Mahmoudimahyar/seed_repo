# Evaluated skill improvement

A completed task can produce a candidate lesson. It does not automatically rewrite an
active skill. Separate project-specific facts from general reusable technique.

1. Record the failure/lesson and source evidence, without private transcripts or secrets.
2. Check the existing skill for the same rule; prefer a small correction to a new skill.
3. Create a branch with the candidate revision and retain the previous version/hash.
4. Test triggering, wrong-trigger cases, procedure success, regressions, cost and review
   effort on development cases and a protected held-out set. Compare with no skill and
   the incumbent when appropriate. Use `seed_eval.py` for exact outputs; reuse Inspect,
   Promptfoo or an approved harness for agent trajectories and domain-specific scoring.
5. A separate reviewer approves promotion. The proposer must not weaken protected evals,
   hard constraints, permissions or its own acceptance criteria. Keep rollback available.
6. After acceptance, run `python3 scripts/seed.py sync-skills --write` to refresh Claude
   mirrors; custom mirror edits are preserved for explicit reconciliation.

Do not update skills after every trivial action. A small number of useful, on-demand
skills beats duplicate role/skill/dispatcher instructions. No autonomous self-modification
service is installed. The evaluation tools support comparative evidence; execution and
promotion use the client's approved controls and the GitHub PR process.
