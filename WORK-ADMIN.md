# Cross-Repository Administration

Global repository registry, cross-domain status, and the master calendar are maintained in `krahd/tom-work-admin`.

This repository remains canonical for **Capturing Collective Memories of the Disappeared with Artificial Intelligence** implementation, prototype and production-system development, technical documentation, tests, data-model and stewardship design, and project-specific research/technical state.

Paper manuscripts and private publication research are canonical in `krahd/research` under `academic-writing/`. Professional/artistic submission packages belong in `krahd/professional-opportunities`; grant/funding/compute application packages and evidence belong in `krahd/grant-applications`.

This project is distinct from `krahd/desaparecidos.uy`.

## Current evaluation state — 14 August 2026

The Level-0 deferred-significance benchmark is documented in `evaluation/DEFERRED-SIGNIFICANCE-EXPERIMENT.md` and has been executed and audited.

Final retained evidence:

- `evaluation/results/deferred-significance-2026-08-14.json`;
- `evaluation/results/deferred-significance-2026-08-14.md`;
- `evaluation/results/deferred-significance-2026-08-14-AUDIT.md`.

Final workflow run `31856109446` at source commit `06eac0f4e74f745684c6f7d24c648b78f580d5ba` passed 16/16 mechanical checks. Main CI on that source commit also passed (`31856109506`). The benchmark verifies only mechanical/researcher-authored properties: preservation before interpretation, later exact-label cross-session emergence without source rewriting, tested non-collapse invariants, and deterministic controller guards. It does not establish live-model interviewing quality or human-memory effects.

The Level-1 live-model policy comparison specified in the same protocol remains the next evaluation gate and requires a configured model endpoint/runtime.

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
3. `krahd/research` or other domain repositories are updated when the change affects manuscripts, submissions, or grants;
4. no stale cross-domain status or date remains in `tom-work-admin`.
