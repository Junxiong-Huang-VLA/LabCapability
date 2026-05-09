# 5.8 Material Library Acceptance Record

Date: 2026-05-09

## Baseline

- Root repo `LabCapability` merged PR #1 into `main`.
  - Merge commit: `30de15f`
  - Handoff archive commit: `128f84d`
- Nested repo `LabSOPGuard_VLA` merged PR #1 into `main`.
  - Merge commit: `b3ee419`
  - Follow-up validated commits: `5460f43`, `2153ebd`
- Baseline tag name for both repos: `v5.8-material-library-accepted`

## Validation

- Root `python -m pytest -q`: `224 passed`
- Root `python -m compileall -q src LabSOPGuard\backend tests`: passed
- Root `scripts/check_project_scope.ps1`: passed
- LabSOPGuard `python -m pytest -q`: `206 passed, 4 skipped`
- LabSOPGuard `python -m compileall -q backend src`: passed
- Frontend `npm run build`: passed
- Frontend `npm test -- --run`: `14 passed`
- LabSOPGuard latest `main` GitHub smoke CI: passed

## Runtime Acceptance

- Formal material library opened at `/materials`.
- Candidate review opened at `/materials/review` through the experiment review route.
- Formal key material count: `74`.
- Canonical action groups present:
  - `hand-paper`
  - `hand-bottle`
  - `hand-spatula`
  - `hand-balance`
  - `hand-container`
- Professional PDF artifacts are kept under `专业报告`.
- Professional PDF artifacts do not appear in the formal key material grid.
- Default candidate review queue excludes rejected, deferred, and not-selected candidates.
- Current 5.8 run showed `pending_total: 0`.

## Stash Review

- Root `codex-final-root-source-wip-20260509` and `codex-post-merge-root-source-wip-20260509` both contain the same candidate approval reason/disposition patch.
- Root `codex-pre-merge-root-local-wip-20260509` contains the same source patch plus obsolete handoff text.
- LabSOPGuard `codex-pre-merge-labsopguard-local-wip-20260509` is covered by the merged PR plus follow-up commits for best-score calibration and material id stabilization.
- These stashes are safe to drop after the P1/P2 follow-up commits are verified.
