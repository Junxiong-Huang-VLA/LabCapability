# Codex Handoff - 2026-05-08 Formal Material Delivery Pipeline

## New Conversation Start

Read and follow:

- `D:\LabCapability\AGENTS.md`
- `D:\LabCapability\docs\codex_2026-05-07_canonical_realityloop_pipeline.md`
- `D:\LabCapability\docs\codex_handoff_2026-05-08_formal_material_delivery_pipeline.md`

Current main experiment:

`2190fe06-3619-45fc-96ef-1bb8afb9bdf9`

Current backend/frontend:

- Backend: `http://127.0.0.1:8001`
- Frontend key-action page: `http://127.0.0.1:5173/experiments/2190fe06-3619-45fc-96ef-1bb8afb9bdf9/key-actions`

## Corrected Formal Delivery Contract

The formal user-facing material handoff folder is not the experiment-local mirror.

Formal delivery root:

`D:\LabCapability\LabSOPGuard\outputs\material_references`

Formal delivery folder naming:

`{experiment_title}_{experiment_date}`

The title/date come from the experiment metadata captured when the experiment is created/analyzed. For the current experiment the formal folder is:

`D:\LabCapability\LabSOPGuard\outputs\material_references\固体称量实验_20260504`

The run-local folder remains only as a compatibility/source mirror:

`D:\LabCapability\LabSOPGuard\outputs\experiments\2190fe06-3619-45fc-96ef-1bb8afb9bdf9\material_references`

## Formal Folder Contents

The formal folder contains:

```text
固体称量实验_20260504/
  关键帧/
  关键片段/
  专业报告/
  素材索引.json
  素材索引.jsonl
  manifest.json
  README.md
```

Current verified formal contents:

- `2` approved keyframes
- `2` approved key clips
- `4` professional report records

Approved keyframe/key-clip filenames use:

`手与被交互对象操作_日期[_序号].扩展名`

Current examples:

- `关键帧\手与容器操作_20260424_02.jpg`
- `关键帧\手与烧杯操作_20260424_02.jpg`
- `关键片段\手与容器操作_20260424.mp4`
- `关键片段\手与烧杯操作_20260424.mp4`

## Pipeline Summary

The fixed pipeline is:

```text
dual-view raw videos
-> view normalization: top_view=third_person, bottom_view=first_person
-> dual-view YOLO scan with first/third-person weights
-> key_action_segments and micro_segments
-> YOLO annotated evidence clips/keyframes
-> local material source staging
-> _material_review_queue candidates
-> qwen3.6-plus VLM advisory review constrained by YOLO evidence packets
-> YOLO evidence recheck
-> frontend/API approval gate
-> formal delivery under LabSOPGuard/outputs/material_references/{title}_{date}
-> professional report sync into the same formal folder
-> published material API and retrieval
```

Important rule:

Candidate/source material must not be treated as formal evidence. Only frontend/API-approved candidates are copied into the formal delivery folder.

## Current Experiment Counts

Current live API and on-disk key-action counts:

- `5` key-action segments
- `8` micro-segments
- `9` raw YOLO hand-object interactions
- `7` API interaction keyframes
- `300` YOLO frame rows

Model contract:

- Key-action VLM assist: `qwen3.6-plus`
- Professional report: `qwen3.6-max-preview`
- Semantic display naming: `qwen3.6-flash`
- `qwen-vl-max` is legacy history, not the fixed default for this pipeline.

## Code Changes Made On 2026-05-08

Changed files:

- `D:\LabCapability\src\key_action_indexer\material_references.py`
- `D:\LabCapability\LabSOPGuard\backend\main.py`
- `D:\LabCapability\tests\test_material_references.py`
- `D:\LabCapability\LabSOPGuard\tests\test_material_publishing.py`
- `D:\LabCapability\docs\codex_2026-05-07_canonical_realityloop_pipeline.md`
- `D:\LabCapability\docs\codex_handoff_2026-05-08_formal_material_delivery_pipeline.md`

Behavioral changes:

- Added `formal_material_references_root(...)`.
- `build_yolo_material_references(...)` now stages validated YOLO source files locally and does not pre-copy candidates into the formal global folder.
- `approve_material_candidates(...)` / `reset_material_references_to_approved_candidates(...)` now promote approved files into the global formal folder.
- The returned approval summary uses the formal folder as `material_references`, while keeping `local_material_references_mirror` for the experiment-local mirror.
- Backend published-material fallback now prefers the global formal folder and falls back to the experiment-local mirror only if needed.
- Current experiment was resynced from approved candidate rows into the global formal folder.
- Backend `8001` was restarted so `/materials/published` reads the global formal folder.

## Current API Checks

After backend restart:

- `/api/v1/experiments/2190fe06-3619-45fc-96ef-1bb8afb9bdf9/materials/published`
  - `total = 4`
  - `source = D:\LabCapability\LabSOPGuard\outputs\material_references\固体称量实验_20260504`
- `/api/v1/experiments/2190fe06-3619-45fc-96ef-1bb8afb9bdf9/key-actions/results`
  - source: `key_action_index_metadata`
  - `5 / 8 / 9 / 7`

## Validation Completed

Commands run:

```powershell
$env:PYTHONPATH='D:\LabCapability\LabSOPGuard;D:\LabCapability\LabSOPGuard\src;D:\LabCapability\src'
python -m pytest tests\test_material_references.py tests\test_material_references_candidates.py LabSOPGuard\tests\test_material_publishing.py::test_experiment_published_materials_prefers_global_formal_delivery_folder -q
```

Result:

`14 passed`

Compile check:

```powershell
python -m compileall -q src LabSOPGuard\backend LabSOPGuard\src tests LabSOPGuard\tests
```

Result:

passed.

## Next Recommendations

If the next session changes anything in this pipeline, preserve:

- dry-run mode without real video or ffmpeg
- `src/key_action_indexer` independence from LabSOPGuard app imports
- formal delivery root under `LabSOPGuard\outputs\material_references`
- folder name from experiment title plus date
- approved keyframe/key-clip names from hand + interacted object plus date
- candidate review gate before formal publication
- current model defaults: `qwen3.6-plus`, `qwen3.6-max-preview`, `qwen3.6-flash`
