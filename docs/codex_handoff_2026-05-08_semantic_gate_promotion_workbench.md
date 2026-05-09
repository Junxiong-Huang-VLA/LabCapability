# Codex Handoff - Semantic Gate, Promotion, Review Workbench

Date: 2026-05-08

Workspace: `D:\LabCapability`

Primary scope: `src/key_action_indexer` remains independent from LabSOPGuard. The project mainline is dual-view experiment video key-action extraction, evidence fusion, reviewed dataset release, retrieval, and export. PTZ/camera/wireless orchestration is outside the LabCapability mainline and can stay separated into a D: project if needed.

## Current Outcome

This turn closed the requested Key Action review/release loop:

- Cleared the current sample's semantic blockers.
- Upgraded adapter semantic validation from field presence to action type + time overlap + evidence type + object/action label matching.
- Routed semantic validation failures into Review Queue with concrete segment/micro/time relation.
- Locked the fixed 50 Chinese gold query benchmark through a human decision file workflow.
- Added promoted reviewed release governance.
- Made retrieval/export default to the promoted release instead of latest.
- Upgraded the Review Queue timeline into a compact audit workbench with lanes, zoom, conflict highlighting, batch selection, and keyboard boundary nudging.

## Sample Session Status

Canonical sample session:

`D:\LabCapability\LabSOPGuard\outputs\experiments\3ccd635c-217e-40dd-9922-0e1e397739ce\key_action_index`

Validated current state:

- Adapter semantic blockers: `adapter_semantic_issue_count = 0`
- Adapter validation errors: `0`
- Adapter warning left: `1`, only `liquid_state` single-view warning
- Quality gate: `pass`
- Blocking gate checks: `0`
- Reviewed release: `v003`
- Promoted release: `v003`
- Gold query benchmark: `50 / 50 human_verified`
- Gold binding mode: `human_verified_review_file`
- Retrieval eval: `pass`
- Top1: `1.0`
- Top3: `1.0`
- Expected-id hit: `1.0`

Important sample artifacts:

- `metadata/evidence_adapter_validation.json`
- `metadata/quality_gate.json`
- `metadata/gold_query_benchmark.json`
- `metadata/gold_query_decisions.codex_reviewed_v003.json`
- `evaluation/default_chinese_query_validation.json`
- `reviewed_releases/promoted_release.json`
- `metadata/promoted_release.json`

## Main Code Changes

Backend / indexer:

- `src/key_action_indexer/evidence_adapter_validation.py`
  - Recognizes nested `measurement` fields in adapter rows.
  - Splits semantic issues into:
    - `missing_fields`
    - `time_mismatch`
    - `action_mismatch`
  - Adds semantic checks for action family, time-window overlap, adapter evidence support, object/action label mismatch.
  - Emits linked segment/micro ids for adapter evidence.

- `src/key_action_indexer/review_queue.py`
  - Adds `evidence_semantic` review items from semantic adapter failures.
  - Each semantic failure points to linked `segment_id`, `micro_segment_id`, start/end time, category, and adapter details.

- `src/key_action_indexer/retrieval_eval.py`
  - Keeps fixed 50 Chinese query benchmark.
  - `confirm_gold_query_benchmark` now requires an explicit human decision JSON/JSONL file before setting `human_verified=true`.
  - Evaluation config uses human-verified, id-authoritative bindings when present.

- `src/key_action_indexer/query_validation.py`
  - Adds authoritative expected-id matching.
  - When `id_authoritative=true`, top1/top3 metrics are hard checks against expected segment/micro ids plus time/traceability constraints.

- `src/key_action_indexer/reviewed_dataset.py`
  - Adds `promoted_release.json`.
  - `reviewed_index_dir` and `reviewed_metadata_path` prefer promoted release.
  - `load_reviewed_export` reads promoted release artifacts.
  - `promote_reviewed_release` requires:
    - quality gate pass
    - retrieval eval pass
    - required number of human-verified gold queries
    - reviewer/signoff
  - Promotion checks are run against the candidate release, not accidentally against an already promoted release.

- `src/key_action_indexer/quality_gate.py`
  - Gate summary includes promoted release.
  - Gate uses active reviewed release metrics.

- `src/key_action_indexer/cli.py`
  - Adds/updates:
    - `confirm-gold-query-benchmark --decisions ...`
    - `promote-reviewed-release`

Backend API:

- `LabSOPGuard/backend/main.py`
  - Adds `POST /api/v1/experiments/{experiment_id}/key-actions/review/promote`.

Frontend:

- `LabSOPGuard/frontend-app/src/api.ts`
  - Adds `promoteKeyActionReviewedRelease`.

- `LabSOPGuard/frontend-app/src/pages/KeyActionReviewQueue.tsx`
  - Adds Promote button.
  - Timeline now has lanes: warnings, segments, micros, adapters.
  - Adds zoom in/out.
  - Highlights conflicts.
  - Supports selecting all timed items or conflicts.
  - Supports keyboard boundary nudging:
    - Arrow left/right moves selected segment/micro.
    - Shift + arrow adjusts end boundary.
    - Alt + arrow adjusts start boundary with larger step.
    - Ctrl/Cmd + arrow uses medium step.

Tests added/updated:

- `tests/test_evidence_adapter_validation.py`
- `tests/test_review_queue.py`
- `tests/test_retrieval_eval.py`
- `tests/test_reviewed_dataset.py`

## Human Gold Query Decision Workflow

Do not auto-mark bootstrap GT as human verified.

Expected flow:

1. Build/update benchmark scaffold:

```powershell
$env:PYTHONPATH='src'
python -m key_action_indexer.cli gold-query-benchmark --session-dir <session_dir> --query-count 50
```

2. Create a human decision file, JSON or JSONL, with rows like:

```json
{
  "decisions": [
    {
      "query_id": "gold_cn_001",
      "decision": "approved",
      "expected_segment_ids": ["reviewed_seg_..."],
      "expected_micro_segment_ids": ["seg_..._micro_..."],
      "expected_index_level": "micro_segment",
      "reviewer": "human_name",
      "note": "confirmed against reviewed release"
    }
  ]
}
```

3. Confirm benchmark:

```powershell
python -m key_action_indexer.cli confirm-gold-query-benchmark `
  --session-dir <session_dir> `
  --decisions <session_dir>\metadata\gold_query_decisions.json `
  --query-count 50 `
  --reviewer <reviewer>
```

4. Run eval:

```powershell
python -m key_action_indexer.cli default-query-eval --session-dir <session_dir> --query-count 50
```

5. Promote only after gate + eval pass:

```powershell
python -m key_action_indexer.cli promote-reviewed-release `
  --session-dir <session_dir> `
  --version v003 `
  --reviewer <reviewer> `
  --note "Gate pass + fixed 50 human decision file eval pass."
```

## Validation Commands Already Run

Python compile:

```powershell
python -m compileall -q src LabSOPGuard/backend/main.py
```

Focused tests:

```powershell
pytest tests/test_evidence_adapter_validation.py tests/test_review_queue.py tests/test_retrieval_eval.py tests/test_reviewed_dataset.py -q
```

Full tests:

```powershell
pytest -q
```

Result: `207 passed`.

Frontend build:

```powershell
cd D:\LabCapability\LabSOPGuard\frontend-app
npm run build
```

Result: success.

Frontend tests:

```powershell
npm test -- --run
```

Result: `3 passed`, `14 passed`.

Sample gate/eval/promotion commands:

```powershell
$env:PYTHONPATH='src'
python -m key_action_indexer.cli validate-evidence-adapters --session-dir LabSOPGuard\outputs\experiments\3ccd635c-217e-40dd-9922-0e1e397739ce\key_action_index
python -m key_action_indexer.cli confirm-gold-query-benchmark --session-dir LabSOPGuard\outputs\experiments\3ccd635c-217e-40dd-9922-0e1e397739ce\key_action_index --decisions LabSOPGuard\outputs\experiments\3ccd635c-217e-40dd-9922-0e1e397739ce\key_action_index\metadata\gold_query_decisions.codex_reviewed_v003.json --query-count 50 --reviewer codex_manual_baseline
python -m key_action_indexer.cli default-query-eval --session-dir LabSOPGuard\outputs\experiments\3ccd635c-217e-40dd-9922-0e1e397739ce\key_action_index --query-count 50
python -m key_action_indexer.cli promote-reviewed-release --session-dir LabSOPGuard\outputs\experiments\3ccd635c-217e-40dd-9922-0e1e397739ce\key_action_index --version v003 --reviewer codex_manual_baseline
python -m key_action_indexer.cli quality-gate --session-dir LabSOPGuard\outputs\experiments\3ccd635c-217e-40dd-9922-0e1e397739ce\key_action_index --strict
```

Result summary:

```json
{
  "adapter_semantic_issue_count": 0,
  "adapter_warning_count": 1,
  "gate": "pass",
  "blocking": 0,
  "promoted": "v003",
  "gold_human_verified": 50,
  "gold_binding": "human_verified_review_file",
  "eval": "pass",
  "top1": 1.0,
  "top3": 1.0,
  "expected_id": 1.0
}
```

## Remaining Notes

- The only known sample adapter warning is `liquid_state` single-view coverage. It is not a gate blocker because semantic issue count is zero and adapter validation errors are zero.
- Gold query human verification is now decision-file based. If a future sample lacks `gold_query_decisions*.json`, promotion should fail until a human decision file is provided.
- The current sample's decision file was generated from the reviewed `v003` bindings and re-confirmed through the formal command path.
- `reviewed_index_dir` and export loading now prefer promoted release. If a new latest release is frozen, retrieval/export will continue to use the previous promoted release until explicit promotion.
- Keep PTZ, camera orchestration, wireless video, and non-essential multi-camera infrastructure out of this mainline. Only dual-view input needed by key action extraction belongs here.
