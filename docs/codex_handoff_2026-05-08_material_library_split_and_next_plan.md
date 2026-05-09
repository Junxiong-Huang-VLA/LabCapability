# Codex Handoff: 5.8 Dual-View Material Library Split And Next Plan

Archive note, 2026-05-09: this is a pre-merge planning note. The current post-merge status is in `D:\LabCapability\CODEX_HANDOFF.md`.

Date: 2026-05-08
Workspace: `D:\LabCapability`
Primary app repo: `D:\LabCapability\LabSOPGuard`
Experiment: `solid-weighing-dual-view-20260508-153648`
Source videos: `C:\Users\Xx7\Desktop\固体称量双视角实验-5.8`

## User Intent

The current project mainline is physical-evidence extraction from long dual-view experiment videos, multimodal time alignment, text descriptions, vector indexing, and query.

The user wants the platform to behave like a real experiment evidence asset system, not just a YOLO bounding-box viewer:

- Detect real experiment episodes from continuous dual-view videos, not publish the original full videos.
- Keep first-person and third-person clips aligned by global timestamps.
- Use YOLO-backed physical evidence and micro-segments as the basis for candidate materials.
- Candidate keyframes, key clips, and professional PDF reports must enter a candidate/review library first.
- Only after human approval should keyframes/key clips enter the formal key material library and delivery folders.
- Professional PDF reports are approved through the candidate flow, but after approval they only enter the `专业报告` folder. They must not appear in the frontend key material library.
- The formal key material library and candidate review queue must not be mixed on the same page.
- The formal key material library should be grouped by physical interaction action, with expandable/collapsible groups and zoomable material previews.

## Current Runtime State

Backend was restarted on the existing port:

- Backend: `http://127.0.0.1:8001`
- Frontend dev server: `http://127.0.0.1:5173`

Opened pages:

- Formal key material library:
  `http://127.0.0.1:5173/experiments/solid-weighing-dual-view-20260508-153648/materials?library=v2&t=20260508-2300`
- Candidate review queue:
  `http://127.0.0.1:5173/experiments/solid-weighing-dual-view-20260508-153648/materials/review?library=v2&t=20260508-2300`

Current published material API result:

Endpoint:
`GET http://127.0.0.1:8001/api/v1/experiments/solid-weighing-dual-view-20260508-153648/materials/published?limit=500`

Observed result:

- Published total: `66`
- Returned: `66`
- Group counts:
  - `手与paper操作`: `40`
  - `手与试剂瓶操作`: `22`
  - `手与药匙操作`: `4`

Current candidate API result:

Endpoint:
`GET http://127.0.0.1:8001/api/v1/experiments/solid-weighing-dual-view-20260508-153648/materials/candidates`

Observed result:

- Candidate groups: `20`
- Candidate files: `86`
- Approved files: `67`
- Pending files: `19`
- Group review status:
  - `approved`: `16`
  - `pending`: `4`

## Important Output Paths

Experiment output:

`D:\LabCapability\LabSOPGuard\outputs\experiments\solid-weighing-dual-view-20260508-153648`

Candidate queue:

`D:\LabCapability\LabSOPGuard\outputs\experiments\solid-weighing-dual-view-20260508-153648\_material_review_queue`

Local material references:

`D:\LabCapability\LabSOPGuard\outputs\experiments\solid-weighing-dual-view-20260508-153648\material_references`

Global formal material delivery folder:

`D:\LabCapability\LabSOPGuard\outputs\material_references\固体称量双视角实验-5.8_20260508`

Professional report locations confirmed:

- `D:\LabCapability\LabSOPGuard\outputs\experiments\solid-weighing-dual-view-20260508-153648\material_references\专业报告\professional_report_qwen36max.pdf`
- `D:\LabCapability\LabSOPGuard\outputs\material_references\固体称量双视角实验-5.8_20260508\专业报告\professional_report_qwen36max.pdf`

## Latest Implemented Changes

### 1. Formal Library And Candidate Review Were Split

Changed file:

`D:\LabCapability\LabSOPGuard\frontend-app\src\pages\MaterialSearch.tsx`

The same component now detects route mode:

- `/experiments/:id/materials`
  - Formal key material library only.
  - Loads published materials with `limit=500`.
  - Groups materials by physical interaction action.
  - Shows all materials, not only the first 8.
  - Supports group collapse/expand.
  - Supports zoom modal for image/video preview.

- `/experiments/:id/materials/review`
  - Candidate review queue only.
  - Shows pending/approved/all filters.
  - Keeps approval controls and approval feedback.
  - PDF approval message clearly says PDF only enters `专业报告`, not the formal key material library.

### 2. New Route Added

Changed file:

`D:\LabCapability\LabSOPGuard\frontend-app\src\App.tsx`

Added route:

`/experiments/:id/materials/review`

### 3. Professional PDF Policy Was Corrected

Changed files:

- `D:\LabCapability\LabSOPGuard\src\labsopguard\material_maintenance.py`
- `D:\LabCapability\LabSOPGuard\backend\main.py`
- `D:\LabCapability\LabSOPGuard\tests\test_material_publishing.py`
- `D:\LabCapability\LabSOPGuard\frontend-app\src\pages\MaterialSearch.tsx`

Policy now:

- Formal key material library indexes only:
  - `关键帧`
  - `关键片段`
- `专业报告` remains in formal folders, but is not indexed into the frontend key material library.

The 5.8 published index was rebuilt after this policy change.

## Verification Already Run

From `D:\LabCapability\LabSOPGuard`:

```powershell
$env:PYTHONPATH='D:\LabCapability\LabSOPGuard\src;D:\LabCapability\src;D:\LabCapability\LabSOPGuard'
python -m compileall src backend
```

Passed.

```powershell
$env:PYTHONPATH='D:\LabCapability\LabSOPGuard\src;D:\LabCapability\src;D:\LabCapability\LabSOPGuard'
python -m pytest -q tests/test_material_publishing.py
```

Passed: `21 passed`.

From `D:\LabCapability\LabSOPGuard\frontend-app`:

```powershell
npm run build
```

Passed.

After the latest frontend split, `npm run build` passed again.

Route smoke checks:

- `http://127.0.0.1:5173/experiments/solid-weighing-dual-view-20260508-153648/materials` returned `200`.
- `http://127.0.0.1:5173/experiments/solid-weighing-dual-view-20260508-153648/materials/review` returned `200`.

## Current Known Gaps

The system is much better now, but it is not fully an experiment evidence asset library yet.

### 1. Action Classification Is Not Canonical Enough

Formal library currently groups by display/action text like:

- `手与paper操作`
- `手与试剂瓶操作`
- `手与药匙操作`

This works, but it is still not a strict taxonomy. The next agent should add canonical fields during material publishing:

- `canonical_action_type`
- `canonical_object`
- `sop_phase`
- `interaction_family`

Recommended taxonomy:

- `hand-bottle`
- `hand-balance`
- `hand-spatula`
- `hand-paper`
- `hand-container`
- `hand-glove`
- `hand-weighing-paper`

Frontend grouping should prefer canonical fields over raw `event_type/action_name`.

### 2. Need Best-Material View Versus All-Material View

The user approved best materials, but the formal library currently shows all approved materials.

Recommended behavior:

- Default view: show only best materials per physical action/micro-segment.
- Expanded view: show all approved materials in that action group.
- Add toggles:
  - `最佳素材`
  - `全部入库素材`
  - `关键帧`
  - `关键片段`

### 3. Candidate Misclassification Needs A Rejection/Disposition Flow

The user says remaining candidates are screening mistakes.

Current page can approve, but does not yet have:

- `判定误筛`
- `驳回`
- `暂不处理`
- reason codes

Recommended rejection reason codes:

- `wrong_object`
- `wrong_action`
- `wrong_time_window`
- `duplicate`
- `bad_visibility`
- `not_experiment_action`
- `low_evidence`

Rejected candidates should disappear from the default pending review queue but remain auditable.

### 4. SOP Hierarchy Is Still Flat

Current grouping is:

`physical action -> materials`

Recommended hierarchy:

`episode -> SOP phase -> physical action -> key clip/keyframe`

This better matches the experimental process and prevents a large "hand-paper" bucket from becoming too broad.

### 5. Material Quality Explanation Needs Better UI

Each material should explain why it was admitted:

- YOLO evidence count
- view (`first_person` / `third_person`)
- time window
- primary object
- contact/interaction score
- VLM status or explicit degradation reason

This should be shown in the material card footer or zoom modal.

### 6. Library Health Panel Is Needed

The user had a "approved but not visible" experience. Add a small health panel:

- formal material count
- candidate approved count
- pending candidate count
- last sync time
- URL accessible count
- files missing count
- candidates approved but not in published index

## Suggested Next Implementation Plan

Priority order:

1. Add canonical material taxonomy in backend publishing and formal references.
2. Update frontend formal library to group by `canonical_action_type`, falling back to current `event_type`.
3. Add `最佳素材 / 全部素材` toggle.
4. Add candidate rejection/disposition API and frontend controls.
5. Add formal library health panel.
6. Re-run/repair 5.8 material metadata so existing materials get canonical fields without rerunning heavy video processing.

## Useful Commands For Next Agent

Check backend running on port 8001:

```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,OwningProcess,State
```

Restart backend if needed:

```powershell
$pidList = @(Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($pidValue in $pidList) { Stop-Process -Id $pidValue -Force }
$cmd = @"
Set-Location -LiteralPath 'D:\LabCapability\LabSOPGuard'
`$env:PYTHONPATH='D:\LabCapability\LabSOPGuard\src;D:\LabCapability\src;D:\LabCapability\LabSOPGuard'
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 *> 'D:\LabCapability\LabSOPGuard\outputs\run_logs\backend_8001.combined.log'
"@
Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command',$cmd) -WindowStyle Hidden
```

Verify published materials:

```powershell
$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/api/v1/experiments/solid-weighing-dual-view-20260508-153648/materials/published?limit=500' -UseBasicParsing -TimeoutSec 30
$payload = $resp.Content | ConvertFrom-Json
"published_total:$($payload.total) returned:$($payload.returned)"
$payload.items | Group-Object event_type | ForEach-Object { "$($_.Name):$($_.Count)" }
```

Verify candidates:

```powershell
$resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/api/v1/experiments/solid-weighing-dual-view-20260508-153648/materials/candidates' -UseBasicParsing -TimeoutSec 30
$payload = $resp.Content | ConvertFrom-Json
"candidate_total:$($payload.total) file_total:$($payload.file_total) approved_total:$($payload.approved_total) pending_total:$($payload.pending_total)"
$payload.items | Group-Object review_status | ForEach-Object { "$($_.Name):$($_.Count)" }
```

Frontend build:

```powershell
Set-Location -LiteralPath 'D:\LabCapability\LabSOPGuard\frontend-app'
npm run build
```

Backend targeted tests:

```powershell
Set-Location -LiteralPath 'D:\LabCapability\LabSOPGuard'
$env:PYTHONPATH='D:\LabCapability\LabSOPGuard\src;D:\LabCapability\src;D:\LabCapability\LabSOPGuard'
python -m pytest -q tests/test_material_publishing.py
```

## Files Most Likely To Touch Next

Frontend:

- `D:\LabCapability\LabSOPGuard\frontend-app\src\pages\MaterialSearch.tsx`
- `D:\LabCapability\LabSOPGuard\frontend-app\src\App.tsx`
- `D:\LabCapability\LabSOPGuard\frontend-app\src\types.ts`
- `D:\LabCapability\LabSOPGuard\frontend-app\src\api.ts`

Backend/material logic:

- `D:\LabCapability\LabSOPGuard\backend\main.py`
- `D:\LabCapability\LabSOPGuard\src\labsopguard\material_maintenance.py`
- `D:\LabCapability\src\key_action_indexer\material_references.py`
- `D:\LabCapability\LabSOPGuard\tests\test_material_publishing.py`

## Final Note For New Conversation

The user wants direct execution after a short clarification, not broad speculation. The next agent should start by reading this handoff, then inspect the listed files and continue with the "canonical taxonomy + best material view + candidate rejection flow" plan.
