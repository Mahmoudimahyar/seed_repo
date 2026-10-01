# Ruleset examples

Both JSON files ship with enforcement disabled and no bypass actors. Review account/plan
capabilities, real reviewer availability, required check identity, and current API schema
before importing/enabling. Do not enable required independent approval with no actual
independent reviewer and then bypass the rule through a fake identity.

The main rule targets the default branch and requires seed-ci-required, linear history,
PR review and protections. The tag rule prohibits modifying/deleting existing v* tags;
control creation permission separately. The files do not configure a merge queue,
production environment, GitHub App identity, or hosted acceptance service.
