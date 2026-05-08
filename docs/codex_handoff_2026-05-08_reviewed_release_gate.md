# Codex Handoff: Reviewed Release Gate Closure

Date: 2026-05-08
Workspace: `D:\LabCapability`

## What Was Completed

- Reviewed dataset freeze now auto-converges coarse/over-covered source segments into micro-window reviewed segments.
- `reviewed_releases/vNNN/` is created on explicit Freeze, including release manifest, diff, reviewed artifacts, reviewed index, and `reviewed_release_export.zip`.
- Retrieval defaults to the latest reviewed release index and metadata.
- Rollback is available through CLI and backend API.
- `metadata/gold_query_benchmark.json` is now the fixed 50-query Chinese benchmark scaffold. Its bindings are marked `bootstrap_auto`, `human_verified=false`, so bootstrap failures do not count as final GT failures.
- Evidence adapter validation now includes semantic support checks and emits `semantic_support_missing` issues.
- Review Queue now receives semantic evidence issues as `evidence_semantic` items.
- Review Queue frontend includes a compact timeline with segment/micro/warning/adapter coverage bars, range-based boundary adjustment, evidence preview, Freeze/apply split, and release rollback.
- Smoke session selection now skips incomplete `key_action_index` directories.

## Current Sample State

Sample:
`D:\LabCapability\LabSOPGuard\outputs\experiments\3ccd635c-217e-40dd-9922-0e1e397739ce\key_action_index`

Latest reviewed release: `v003`

Reviewed metrics:

- reviewed segments: 8
- reviewed micro segments: 8
- reviewed vectors: 16
- coverage ratio: 0.422262
- longest segment ratio: 0.205501
- reviewed unreviewed count: 0

Quality gate now fails only on explicit manual evidence blockers:

- `adapter_semantic_issue_count = 20`
- Review Queue has 20 `evidence_semantic` items.

The previous coverage/longest-segment blockers are converged by the reviewed release.

## Important Files

- `src/key_action_indexer/reviewed_dataset.py`
- `src/key_action_indexer/quality_gate.py`
- `src/key_action_indexer/review_queue.py`
- `src/key_action_indexer/evidence_adapter_validation.py`
- `src/key_action_indexer/retrieval_eval.py`
- `src/key_action_indexer/query_validation.py`
- `src/key_action_indexer/health_report.py`
- `LabSOPGuard/backend/main.py`
- `LabSOPGuard/frontend-app/src/pages/KeyActionReviewQueue.tsx`
- `LabSOPGuard/frontend-app/src/api.ts`
- `LabSOPGuard/frontend-app/src/types.ts`
- `scripts/run_key_action_smoke.ps1`

## Commands Verified

```powershell
pytest -q
npm run build
npm test -- --run
./scripts/run_key_action_smoke.ps1 -SkipPytest -SkipFrontend
```

Results:

- `pytest -q`: 198 passed
- frontend build: passed
- frontend tests: 14 passed
- smoke without duplicate pytest/frontend: passed

## Useful Next Commands

```powershell
python -m key_action_indexer.cli freeze-reviewed-dataset --session-dir <key_action_index>
python -m key_action_indexer.cli rollback-reviewed-release --session-dir <key_action_index>
python -m key_action_indexer.cli gold-query-benchmark --session-dir <key_action_index> --overwrite
python -m key_action_indexer.cli default-query-eval --session-dir <key_action_index> --query-count 50
python -m key_action_indexer.cli quality-gate --session-dir <key_action_index> --strict
```

## Remaining Manual Work

- Review the 20 semantic adapter issues and decide whether adapter rows need richer fields or should be accepted with notes.
- Human-verify the 50 gold query expected segment/micro bindings, then flip `human_verified=true` for final GT.
- Retrieval top1/top3 is intentionally reported but not treated as final failure while benchmark bindings are bootstrap-only.
