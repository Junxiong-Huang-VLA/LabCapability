# Codex Handoff - LabCapability

Generated: 2026-05-09 09:00:00 +08:00

## Current State

This workspace has moved past the two-PR handoff stage. Both pull requests were merged on 2026-05-09 UTC+08 workflow time:

- Root repo `D:\LabCapability`: `Junxiong-Huang-VLA/LabCapability#1` merged, merge commit `30de15fcc976012fcf0b86d468cb6f7bd5d038aa`.
- Nested repo `D:\LabCapability\LabSOPGuard`: `Junxiong-Huang-VLA/LabSOPGuard_VLA#1` merged, merge commit `b3ee4197d273e29875f809486a12503f95cb42f7`.
- Nested repo received one post-merge main commit: `5460f435e84b1339e40ed8acb97875ccab97202d` (`feat: add material best score calibration`), and GitHub CI passed.

Both local repos are intended to be on `main` tracking `origin/main`.

## Scope Boundaries

- Root repo owns `src/key_action_indexer`, key-action indexing, review/promotion gates, gold benchmark, report artifacts, and retrieval gates.
- Nested repo owns LabSOPGuard integration surfaces: key-action upload entry, review pages, material candidate display, and API wiring.
- Keep `src/key_action_indexer` independent from the LabSOPGuard app.
- Mainline scope remains physical-evidence extraction from long dual-view experiment videos, multimodal time alignment, text descriptions, vector indexing, and query.
- Current priority remains YOLO-backed key action segments, hand-object interaction evidence, micro-segments, multiview clip alignment, metadata, and retrieval.
- Do not reintroduce PTZ, cloud PTZ, five-camera orchestration, camera port mapping, MQTT tooling, wireless-video SDKs, `/api/v1/cameras`, or multi-monitor recording endpoints.
- PTZ lives separately at `D:\PtzTracker`.
- Multi-camera and wireless-video monitoring lives separately at `D:\MultiCameraMonitor`.

## Validation Completed

Root repo `D:\LabCapability`:

```text
python -m pytest -q
224 passed

python -m compileall -q src LabSOPGuard\backend tests
passed

powershell -ExecutionPolicy Bypass -File D:\LabCapability\scripts\check_project_scope.ps1
Scope guard passed
```

Nested repo `D:\LabCapability\LabSOPGuard`:

```text
python -m pytest -q
206 passed, 4 skipped, 7 warnings

python -m compileall -q backend src
passed

frontend-app npm run build
passed

frontend-app npm test -- --run
14 passed
```

GitHub Actions:

```text
LabSOPGuard_VLA main CI for 5460f435e84b1339e40ed8acb97875ccab97202d passed.
```

## Runtime Acceptance

Local services were restarted and verified:

- Backend: `http://127.0.0.1:8001`
- Frontend: `http://127.0.0.1:5173`

5.8 experiment checked:

- Experiment id: `solid-weighing-dual-view-20260508-153648`
- Formal material page: `/experiments/solid-weighing-dual-view-20260508-153648/materials`
- Candidate review page: `/experiments/solid-weighing-dual-view-20260508-153648/materials/review`

Observed formal material API:

```text
published_total: 74
returned: 74
taxonomy: hand-bottle, hand-balance, hand-spatula, hand-paper, hand-container
hand-paper: 40
hand-balance: 2
hand-container: 2
hand-bottle: 22
hand-spatula: 8
report_rows: 0
```

Observed candidate API:

```text
candidate_total: 20
file_total: 86
pending: 0
approved: 75
rejected: 0
deferred: 0
not_selected: 11
```

Professional report PDFs exist in `专业报告` folders and do not appear in the formal key material grid.

## Local Stashes

Two local stashes were intentionally preserved:

- Root repo: `codex-post-merge-root-source-wip-20260509`, containing an unmerged source-code sketch in `src/key_action_indexer/material_references.py`.
- Root repo: `codex-pre-merge-root-local-wip-20260509`, original mixed handoff/source stash from before merge.
- Nested repo: `codex-pre-merge-labsopguard-local-wip-20260509`, old pre-merge WIP. Much of its best-score/calibration work was already committed to main as `5460f435...`; inspect before applying.

Do not blindly apply or drop these stashes. Inspect them first if continuing follow-up work.

## Next Suggested Work

1. Keep both repos on `main` and verify clean status before new feature work.
2. If continuing material quality work, start from nested commit `5460f435...` and compare against preserved stash before editing.
3. The next product step is SOP hierarchy refinement: `episode -> SOP phase -> physical action -> key clip/keyframe`.
4. Keep candidate disposition auditable; do not fabricate human approval.
