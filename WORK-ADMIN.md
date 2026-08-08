# Cross-Repository Administration

Global repository registry, cross-domain status, and the master calendar are maintained in `krahd/tom-work-admin`.

This repository remains canonical for **Capturing Collective Memories of the Disappeared with Artificial Intelligence** implementation, prototype and production-system development, technical documentation, tests, data-model and stewardship design, and project-specific research/technical state.

Paper manuscripts and publication artefacts remain canonical in `krahd/academic-writing`. Professional/artistic submission packages belong in `krahd/professional-opportunities`; grant/funding/compute application packages and evidence belong in `krahd/grant-applications`.

This project is distinct from `krahd/desaparecidos.uy`.

## Mandatory synchronisation rule

`krahd/tom-work-admin` **must be kept current** whenever work here materially changes the project's administratively meaningful state. Updating the administration repository is part of completing the change, not optional later cleanup.

Update this repository first for substantive implementation/research changes, then update `krahd/tom-work-admin` in the same work session when any of the following changes:

- project lifecycle state, scope, research question, implementation goal, or governance direction;
- prototype/production architecture, model/provider dependency, deployment state, evaluation status, data-capture readiness, ethics/governance gate, or major validation result;
- relationship to a manuscript, submission, grant, collaborator, institution, repository, dataset, or other cross-domain dependency;
- deadline, collaboration meeting, submission/publication outcome, deployment period, or other material cross-domain date;
- current next action or major research/validation gate.

## Ownership boundary

Keep implementation, technical tests, research-system design, data/stewardship evidence, and project-specific state here. `tom-work-admin` stores only the concise cross-repository view and must point back to canonical project sources rather than duplicate them.

## Completion check

Before considering a material project-state change complete, verify that:

1. this repository reflects the substantive change;
2. `krahd/tom-work-admin` reflects any resulting global status, date, relationship, or next-action change;
3. `krahd/academic-writing` or other domain repositories are updated when the change affects manuscripts, submissions, or grants;
4. no stale cross-domain status or date remains in `tom-work-admin`.
