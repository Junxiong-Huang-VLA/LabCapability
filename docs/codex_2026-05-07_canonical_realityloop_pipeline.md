# 2026-05-07 RealityLoop Canonical Pipeline

This document is the fixed 2026-05-07 contract for the current RealityLoop key-action experiment-analysis flow. It reconciles the Codex handoff history for pipeline, model choice, delivery folders, PDF generation, frontend behavior, and project-level smoke/optimization work.

## Current Experiment

- Experiment ID: `2190fe06-3619-45fc-96ef-1bb8afb9bdf9`
- Current authoritative source: `LabSOPGuard/outputs/experiments/2190fe06-3619-45fc-96ef-1bb8afb9bdf9/key_action_index`
- Current verified key-action counts from the live API and on-disk `key_action_index` files: `5` segments, `8` micro-segments, `9` raw YOLO hand-object interactions, and `7` API interaction keyframes.
- Earlier `6 / 7 / 64` and `6 / 5 / 64` handoff summaries are superseded for this checkout unless the dual-view YOLO pipeline is rerun and produces those counts again.
- Current formal delivery after review sync: `4` professional report records, `2` approved keyframes, and `2` approved key clips in `LabSOPGuard/outputs/material_references/固体称量实验_20260504`.
- View mapping is fixed as `top/top_view/overview -> third_person` and `bottom/bottom_view/fpv/egocentric -> first_person`.

## Model Contract

- Third-person YOLO weights: `LabSOPGuard/models/yolo/third_person/best.pt`
- First-person YOLO weights: `LabSOPGuard/models/yolo/first_person/best.pt`
- Key-action VLM assist model: `KEY_ACTION_VLM_MODEL`, falling back to `QWEN_VL_MODEL`, then `VLM_MODEL`, then `qwen3.6-plus`.
- Professional PDF report model: `QWEN_REPORT_MODEL`, default `qwen3.6-max-preview`.
- Semantic material display-name model: `MATERIAL_DISPLAY_NAME_QWEN_MODEL`, default `qwen3.6-flash`.
- `qwen-vl-max` is legacy history only and is not the fixed 2026-05-07 default for this pipeline.

## End-To-End Flow

```text
dual-view raw video upload
-> view normalization and manifest creation
-> dual-view YOLO scan with first/third-person weights
-> YOLO-backed boundary refinement
-> key_action_segments and micro_segments
-> aligned first/third-person clips and keyframes
-> YOLO annotated segment clips
-> material reference source build from YOLO physical evidence
-> review candidates in _material_review_queue
-> VLM advisory review constrained by YOLO evidence packet
-> frontend candidate review and approval
-> approved LabSOPGuard/outputs/material_references/{experiment_title}_{experiment_date}/关键帧 and 关键片段
-> professional report generation with qwen3.6-max-preview
-> report sync into material_references/专业报告
-> material publishing, semantic display naming, vector index, retrieval
-> key-actions/status, key-actions/results, analysis-overview, report page
```

## Candidate And Delivery Folders

- Canonical review queue: `_material_review_queue`
- Legacy read-only fallback: `material_candidates`
- Formal delivery root after approval: `LabSOPGuard/outputs/material_references`
- Formal delivery folder name: `{experiment_title}_{experiment_date}`, using the title/date captured when the experiment is created/analyzed.
- Run-local mirror for compatibility: `LabSOPGuard/outputs/experiments/{experiment_id}/material_references`
- Formal subfolders:
  - `LabSOPGuard/outputs/material_references/{experiment_title}_{experiment_date}/关键帧`
  - `LabSOPGuard/outputs/material_references/{experiment_title}_{experiment_date}/关键片段`
  - `LabSOPGuard/outputs/material_references/{experiment_title}_{experiment_date}/专业报告`
- Approved keyframe/key-clip filenames use the hand-object physical action and date, for example `手与容器操作_20260424_02.jpg` and `手与烧杯操作_20260424.mp4`.
- Candidate files never become formal evidence until a frontend/API approval call promotes the recommended candidate files.
- Professional report artifacts are copied into the same formal delivery folder under `专业报告`.

## Frontend Contract

- `KeyActionIndex.tsx` must render media through experiment file API URLs, never local `file:///D:/...` paths.
- The key-action page must read real `key_action_index` metadata and show the current `5 / 8 / 9 / 7` evidence counts for the current experiment.
- Candidate review UI must expose YOLO validity, VLM advisory status, pipeline status, recommendation count, and approval action.
- `ExperimentList.tsx` keeps the 2026-05-07 optimizations: paginated list loading beyond the first 100 rows, archive/unarchive state sync, null confidence as empty, search over cleaned mojibake-repaired display text, and mobile-safe controls.
- Workspace/published material previews use bounded API limits and frontend-safe media URLs.

## Project Optimizations To Preserve

- Dry-run mode must not require real videos or ffmpeg.
- Dry-run inventory scans only the current session output by default and must not traverse historical LabSOPGuard outputs.
- Non-label session context seeding writes `metadata/session_context_events.jsonl` from manifest/video/pipeline metadata and clears `thin_multimodal_context` without inventing manual labels.
- Evidence-reference parsing supports dict/list/string/JSON-string refs and resolves model observation, video understanding, state-change, and material-catalog references into review bundles.
- Capability-gap reporting emits `annotation_plan`, `minimum_label_targets`, `blocking_unavailable_capabilities`, and runnable relabel commands.
- YOLO relabel export supports candidate packs for missing classes and marks unreviewed candidates as `candidate_unreviewed`.
- Micro-GT and evaluation tooling distinguishes template/prediction-seeded rows from formal labels, and only marks precision/recall formal when GT is complete.
- Health and browser smoke scripts remain part of the regression loop:
  - `scripts/check_key_action_outputs.ps1`
  - `scripts/run_key_action_smoke.ps1`
  - `scripts/frontend_smoke.ps1`
  - `scripts/frontend_smoke_check.js`

## Acceptance Checks

Before treating this pipeline as fixed, keep these checks green:

```powershell
python -m compileall -q src LabSOPGuard\backend LabSOPGuard\src tests LabSOPGuard\tests
python -m pytest -q
cd LabSOPGuard\frontend-app
npm run build
```

For the current experiment, the API should expose YOLO annotated clips for both views, formal material references after approval, professional report artifacts, and key-action counts from `key_action_index_metadata`, not stale root manifest actions.
