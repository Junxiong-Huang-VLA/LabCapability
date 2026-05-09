# Codex Handoff - Workspace Formal Material Delivery Closure

Date: 2026-05-08
Workspace: `D:\LabCapability`
Primary app: `D:\LabCapability\LabSOPGuard`

## Completed Scope

This handoff closes the formal material delivery follow-up batch around workspace published materials, frontend preview, diagnostics, lifecycle health, and regression smoke.

### 1. Fixed MaterialSearch Smoke

Added a repeatable Playwright smoke script:

- Script: `D:\LabCapability\LabSOPGuard\frontend-app\scripts\material-search-smoke.mjs`
- NPM command: `npm run smoke:materials`
- Default experiment: `2190fe06-3619-45fc-96ef-1bb8afb9bdf9`

The smoke checks:

- Workspace `/api/v1/materials/published` has 4 formal materials for the current experiment.
- 2 formal keyframes expose and load image URLs.
- 2 formal clips expose and load video URLs.
- Experiment `MaterialSearch` shows pending count = 0.
- Diagnostics panel has 4 rows and all formal URLs are accessible.
- Semantic search terms still hit current formal materials:
  - `烧杯` >= 2
  - `容器操作` >= 2
  - `戴手套操作` >= 4
  - `pouring liquid` >= 2

Live smoke result:

```text
npm run smoke:materials
status: passed
workspace_materials: 4
formal_images: 2
formal_videos: 2
pending: 0
```

### 2. Global Workspace Material Search UI

Added a real workspace-level frontend route:

- Route: `/materials`
- Page: `D:\LabCapability\LabSOPGuard\frontend-app\src\pages\WorkspaceMaterials.tsx`
- API consumer: `workspaceMaterialApi.getPublishedMaterials(...)`
- Backend endpoint consumed: `/api/v1/materials/published`

The global page now:

- Reads the workspace published index directly.
- Displays formal `preview_url` images and `clip_url` videos.
- Supports text search against workspace FTS.
- Supports an experiment ID filter, useful for smoke and scoped review.
- Shows lifecycle health status from `/api/v1/materials/published/health`.

Navigation was added to the shared layout as `全局素材 Materials`.

### 3. Evidence Chain Diagnostics UI

The experiment material page now renders a lightweight diagnostics panel:

- Page: `D:\LabCapability\LabSOPGuard\frontend-app\src\pages\MaterialSearch.tsx`
- API consumer: `experimentApi.getMaterialDiagnostics(id)`
- Backend endpoint: `/api/v1/experiments/{experiment_id}/materials/diagnostics`

The panel exposes per formal material:

- Candidate ID and candidate group ID
- Approval status and approver
- YOLO recheck status and valid evidence count
- VLM model/status
- Source candidate file
- Formal stored file
- Formal URL accessibility

This keeps the contract visible: candidate material is not final evidence until approved and delivered as a formal material reference.

### 4. Workspace Published Index Lifecycle Guard

Added backend lifecycle health for workspace published materials:

- Function: `check_workspace_published_materials_lifecycle(...)`
- Source: `D:\LabCapability\LabSOPGuard\src\labsopguard\material_maintenance.py`
- API: `GET /api/v1/materials/published/health?auto_rebuild=true`

The guard checks:

- SQLite index existence and modified time
- Latest formal/published source modified time
- SQLite material count
- Expected deduplicated workspace material count
- Formal JSONL material count
- Formal report count
- Warnings for missing, stale, or count-mismatched indexes

`GET /api/v1/materials/published` now performs lifecycle checking with `auto_rebuild=true` before querying, so stale global results should self-heal.

Important live health snapshot after the fix:

```text
status: ok
sqlite_count: 270
expected_indexable_count: 270
formal_jsonl_material_count: 84
formal_report_count: 36
experiment_count: 16
```

### 5. Semantic Regression Contract

The formal material semantic contract is now covered in two places:

- Python regression:
  - `D:\LabCapability\LabSOPGuard\tests\test_material_publishing.py`
  - verifies `烧杯`, `容器操作`, `戴手套操作`, `pouring liquid`
- Playwright smoke:
  - `D:\LabCapability\LabSOPGuard\frontend-app\scripts\material-search-smoke.mjs`
  - verifies the same terms against the live workspace API and global page

## Key Files Changed

- `D:\LabCapability\LabSOPGuard\backend\main.py`
  - Workspace published health API
  - Published-material query lifecycle guard
  - Existing diagnostics and media URL path are consumed by frontend

- `D:\LabCapability\LabSOPGuard\src\labsopguard\material_maintenance.py`
  - Formal material fallback indexing
  - Semantic FTS enrichment
  - Workspace published lifecycle scanner and auto rebuild

- `D:\LabCapability\LabSOPGuard\frontend-app\src\pages\WorkspaceMaterials.tsx`
  - New global workspace formal material search page

- `D:\LabCapability\LabSOPGuard\frontend-app\src\pages\MaterialSearch.tsx`
  - Diagnostics panel
  - Stable smoke selectors for formal image/video/pending checks

- `D:\LabCapability\LabSOPGuard\frontend-app\scripts\material-search-smoke.mjs`
  - Fixed smoke script

- `D:\LabCapability\LabSOPGuard\tests\test_material_publishing.py`
  - Lifecycle health rebuild regression
  - Formal semantic search regression

- `D:\LabCapability\LabSOPGuard\tests\test_material_diagnostics.py`
  - Formal evidence chain diagnostics regression

## Verification Completed

All validation below completed successfully:

```text
python -m compileall -q src LabSOPGuard\backend LabSOPGuard\src tests LabSOPGuard\tests

python -m pytest -q
194 passed in 169.61s

cd LabSOPGuard\frontend-app
npm run build

npm run smoke:materials
status: passed
```

## Runtime Notes

During live smoke, backend was restarted on:

```text
http://127.0.0.1:8001
```

Frontend dev server was already available on:

```text
http://127.0.0.1:5173
```

The smoke assumes both servers are running. It uses the frontend Vite proxy for `/api/v1/...` and sends `X-Operator-Role: admin` for workspace-level published material APIs.

Environment overrides:

```text
MATERIAL_SMOKE_BASE_URL
MATERIAL_SMOKE_EXPERIMENT_ID
MATERIAL_SMOKE_OPERATOR_ROLE
MATERIAL_SMOKE_REINDEX=0
MATERIAL_SMOKE_EXPECTED_MATERIALS
MATERIAL_SMOKE_EXPECTED_IMAGES
MATERIAL_SMOKE_EXPECTED_VIDEOS
```

## Suggested Next Thread Starting Point

Start from the new global route `/materials` and the fixed smoke command `npm run smoke:materials`.

Good next checks:

- Whether the global page needs role/experiment scoping controls for non-admin reviewers.
- Whether lifecycle health should surface in an ops dashboard, not only the global material page.
- Whether diagnostics should allow export as a formal evidence-chain report.
