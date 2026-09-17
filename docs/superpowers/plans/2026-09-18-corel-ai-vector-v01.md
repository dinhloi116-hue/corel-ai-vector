# Corel AI Vector V0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a one-file installer for CorelDRAW 2025/v26 that adds `Launch > Corel AI Vector`, opens a Vietnamese Docker, exports the selected bitmap, securely stores an OpenAI API key, calls an AI Geometry Director with structured output, converts a geometry plan into editable Corel curves, and provides explicit cost controls.

**Architecture:** Reuse the proven Corel Addons + browser Docker + Launch-script pattern. Corel/HTML JavaScript owns selection export, image-space geometry solving and Corel curve creation. A local PowerShell bridge owns DPAPI key storage and OpenAI Responses API HTTPS calls. AI returns a geometry plan rather than final SVG; local code enforces line/cubic structure and smooth joins.

**Tech Stack:** CorelDRAW 2025/v26 JavaScript object model, HTML/CSS/ES5-compatible JavaScript, PowerShell 5.1+, Windows DPAPI, OpenAI Responses API, JSON Schema, one-file CMD installer, Node.js only for repository-side static tests.

**Spec:** `docs/superpowers/specs/2026-09-18-ai-guided-corel-tool-design.md`

## Global Constraints

- Target CorelDRAW 2025 / v26 first.
- Installer is one file and must remove only previous `CorelAIVector*` installation files.
- Installer must not delete or modify unrelated Launch items and must not touch Refine PRO.
- Source bitmap must remain unchanged by default.
- Generated geometry must be real editable Corel Curve objects.
- A visually kinked smooth region is a hard failure even if pixel overlap is high.
- AI output must be structured JSON; arbitrary SVG output is forbidden.
- API key must never enter the public repository or plain-text settings.
- API spending is disabled until the user explicitly stores a key and enables a non-zero budget.
- Default maximum AI passes per glyph is 2.
- `gpt-5.6-terra` is the default Geometry Director model; Luna is allowed for cheap checks and Sol only for explicit high-accuracy retry.

---

## File structure

```text
corel/
├─ payload/
│  ├─ CorelDrw.addon
│  ├─ AppUI.xslt
│  ├─ UserUI.xslt
│  ├─ CorelAIVector.html
│  ├─ CorelAIVectorCore.js
│  ├─ CorelAIVectorGeometry.js
│  ├─ CorelAIVectorBridge.ps1
│  ├─ CorelAIVector_00_MO_GIAO_DIEN.js
│  └─ version.json
├─ installer/
│  └─ build_installer.py
└─ tests/
   ├─ test_payload.js
   ├─ test_geometry.js
   └─ test_installer.py
release/
└─ CAI_COREL_AI_VECTOR_V0_1.cmd
```

---

### Task 1: Build a safe Corel Addon + Launch shell

**Files:**
- Create: `corel/payload/CorelDrw.addon`
- Create: `corel/payload/AppUI.xslt`
- Create: `corel/payload/UserUI.xslt`
- Create: `corel/payload/CorelAIVector.html`
- Create: `corel/payload/CorelAIVector_00_MO_GIAO_DIEN.js`
- Create: `corel/payload/version.json`
- Create: `corel/tests/test_payload.js`

**Interfaces:**
- Docker GUID: `{7FAF4D04-1B42-4C50-AEC4-4B2A59A4A801}`
- Browser item GUID: `{94D0B409-C5A6-4477-A3D9-63B6E49C4F31}`
- Launch script opens Docker using `host.FrameWork.ShowDialog`.

- [ ] **Step 1: Write static payload tests**

```js
const fs = require('fs');
const assert = require('assert');
const root = 'corel/payload';
const app = fs.readFileSync(`${root}/AppUI.xslt`, 'utf8');
const open = fs.readFileSync(`${root}/CorelAIVector_00_MO_GIAO_DIEN.js`, 'utf8');
assert(app.includes('7FAF4D04-1B42-4C50-AEC4-4B2A59A4A801'));
assert(app.includes('CorelAIVector.html'));
assert(open.includes('ShowDialog'));
console.log('payload shell PASS');
```

- [ ] **Step 2: Run and verify the test fails before files exist**

Run: `node corel/tests/test_payload.js`
Expected: missing-file failure.

- [ ] **Step 3: Implement AppUI/UserUI and launch script**

`AppUI.xslt` must add one browser item and one dialog only. `UserUI.xslt` must add a reference to that dialog without deleting existing UI nodes.

Open script:

```js
(function(){
  var GUID = '7FAF4D04-1B42-4C50-AEC4-4B2A59A4A801';
  try { host.FrameWork.ShowDialog(GUID); }
  catch (e) { host.FrameWork.ShowMessageBox('Corel AI Vector chưa nạp giao diện. Hãy khởi động lại CorelDRAW.\n\n'+(e.message||e), 'Corel AI Vector'); }
})();
```

- [ ] **Step 4: Create minimal Docker UI**

The initial UI must contain buttons `KIỂM TRA COREL`, `VẼ CURVE TEST`, `API / NGÂN SÁCH`, and a status box. It must use `window.external.Application` only after the user opens the Docker.

- [ ] **Step 5: Run static test**

Run: `node corel/tests/test_payload.js`
Expected: PASS.

---

### Task 2: Add Corel curve writer with a smooth fixture

**Files:**
- Create: `corel/payload/CorelAIVectorCore.js`
- Create: `corel/payload/CorelAIVectorGeometry.js`
- Create: `corel/tests/test_geometry.js`
- Modify: `corel/payload/CorelAIVector.html`

**Interfaces:**
- `CAIV.buildCurveFromPlan(app, plan, placement) -> Shape`
- `CAIV.solveSegment(anchor0, anchor1, tangent0Deg, tangent1Deg, outRatio, inRatio) -> {c1,c2}`

- [ ] **Step 1: Write pure geometry tests**

```js
const assert = require('assert');
const G = require('../payload/CorelAIVectorGeometry.js');
const s = G.solveSegment({x:0,y:0},{x:100,y:0},0,180,0.33,0.33);
assert(Math.abs(s.c1.y) < 1e-9);
assert(Math.abs(s.c2.y) < 1e-9);
assert(s.c1.x > 0 && s.c2.x < 100);
console.log('geometry PASS');
```

- [ ] **Step 2: Implement geometry helper as UMD/ES5 module**

Control points are derived from chord length and tangent direction. For a smooth join shared by two spans, the outgoing/incoming tangent direction must be identical after normalization.

- [ ] **Step 3: Implement `buildCurveFromPlan`**

Use Corel object-model calls:

```js
var crv = app.CreateCurve(doc);
var sp = crv.CreateSubPath(x0, y0);
sp.AppendLineSegment(x1, y1, false);
sp.AppendCurveSegment2(x2, y2, c1x, c1y, c2x, c2y, false);
sp.Closed = true;
var shape = doc.ActiveLayer.CreateCurve(crv);
```

Wrap creation in one document command group and name generated shapes with prefix `CAIV_`.

- [ ] **Step 4: Add `VẼ CURVE TEST` button**

The fixture draws a four-cubic smooth oval beside the current selection. This proves true Corel curve construction before paid AI is enabled.

- [ ] **Step 5: Run geometry tests**

Run: `node corel/tests/test_geometry.js`
Expected: PASS.

---

### Task 3: Export the selected Corel object to a temporary PNG

**Files:**
- Modify: `corel/payload/CorelAIVectorCore.js`
- Modify: `corel/payload/CorelAIVector.html`
- Modify: `corel/tests/test_payload.js`

**Interfaces:**
- `CAIV.exportSelectionPng(app, path, maxPx) -> {path,width,height,docWidth,docHeight,left,bottom}`

- [ ] **Step 1: Add static test requiring the export code path**

The test asserts that `CorelAIVectorCore.js` contains numeric constants `cdrPNG=802` and `cdrSelection=2` and calls `ExportBitmap`.

- [ ] **Step 2: Implement selection validation**

Reject no selection and reject more than one selected object for V0.1. Keep the selected object unchanged.

- [ ] **Step 3: Export at bounded resolution**

Use `Document.ExportBitmap` with PNG filter `802`, selection range `2`, RGB image type `4`, normal antialiasing `1`, and call `Finish()` on the returned filter. Preserve aspect ratio and cap the long side at `1600` px.

- [ ] **Step 4: Add `XUẤT ẢNH TEST` button**

Show the output temp path and dimensions in the status box; do not yet send it to AI.

---

### Task 4: Implement encrypted API key storage and local bridge self-test

**Files:**
- Create: `corel/payload/CorelAIVectorBridge.ps1`
- Modify: `corel/payload/CorelAIVector.html`
- Create: `corel/tests/test_installer.py`

**Interfaces:**
- Bridge actions: `save-key`, `has-key`, `delete-key`, `self-test`, `run-job`
- Settings directory: `%LOCALAPPDATA%\CorelAIVector`
- Key file: `%LOCALAPPDATA%\CorelAIVector\api_key.dpapi`

- [ ] **Step 1: Add bridge contract test**

Repository-side Python test reads the script and asserts all five action names exist and that `Protect-CmsMessage`/plain-text persistence are not used. It requires `[Security.Cryptography.ProtectedData]` DPAPI use.

- [ ] **Step 2: Implement DPAPI key functions**

`save-key` converts UTF-8 bytes and uses `ProtectedData.Protect(..., CurrentUser)`. `run-job` uses `ProtectedData.Unprotect` only in process memory.

- [ ] **Step 3: Implement bridge self-test**

`self-test` verifies PowerShell version, TLS 1.2 support, app-data write access and key presence without making an API request.

- [ ] **Step 4: Add API settings UI**

The Docker lets the user paste a key once, save it, verify that a protected key exists, or delete it. It never reads the decrypted key back into the browser UI.

---

### Task 5: Add the Geometry Director JSON schema and prompt

**Files:**
- Create: `corel/payload/geometry_schema.json`
- Create: `corel/payload/geometry_prompt.txt`
- Create: `corel/tests/test_schema.js`

**Interfaces:**
- Schema name: `corel_ai_vector_geometry_plan`
- Schema version: `1`

- [ ] **Step 1: Write schema validator test**

The Node test loads JSON and requires all object schemas to set `additionalProperties:false`; path regions must define `kind`, `start`, `end`, tangents, continuity and anchor policy.

- [ ] **Step 2: Write the Geometry Director prompt**

The prompt explicitly says:

```text
Do not trace every pixel.
Do not beautify or substitute a font.
Use the fewest anchors that preserve the design.
Mark true corners as sharp_corner.
Keep long smooth arcs continuous.
Do not place anchors merely because raster edges are jagged.
Return JSON only through the supplied schema.
```

- [ ] **Step 3: Add schema fixture tests**

Include one `0` plan with outer+counter paths and one `1` plan with line/corner/smooth regions.

---

### Task 6: Implement the OpenAI Responses bridge without spending during tests

**Files:**
- Modify: `corel/payload/CorelAIVectorBridge.ps1`
- Create: `corel/payload/version.json`
- Modify: `corel/tests/test_installer.py`

**Interfaces:**
- Endpoint: `https://api.openai.com/v1/responses`
- Default model: `gpt-5.6-terra`
- Input image sent as data URL in `input_image`
- Structured output configured with `text.format.type = json_schema`

- [ ] **Step 1: Add static request-shape test**

The test requires the request body to contain `model`, `input`, `input_image`, `text.format`, `json_schema`, `strict`, and `store=false`.

- [ ] **Step 2: Implement request construction**

`run-job` reads a job JSON containing image path, prompt path, schema path, requested model, pass type and budget metadata. It Base64-encodes the PNG and sends a Responses API request.

- [ ] **Step 3: Parse the returned structured text**

Extract the response's output text, validate it parses as JSON, write `result.json`, and write token usage to `usage.json`.

- [ ] **Step 4: No live call in CI/local development**

Tests exercise request construction using `-DryRun`, which writes the request JSON without sending HTTPS.

---

### Task 7: Add budget and cost controls

**Files:**
- Modify: `corel/payload/CorelAIVectorCore.js`
- Modify: `corel/payload/CorelAIVectorBridge.ps1`
- Modify: `corel/payload/CorelAIVector.html`

**Interfaces:**
- Budget file: `%LOCALAPPDATA%\CorelAIVector\budget.json`
- Usage log: `%LOCALAPPDATA%\CorelAIVector\usage.jsonl`

- [ ] **Step 1: Implement default zero budget**

No `run-job` request is sent when budget is zero. The user must explicitly set a positive monthly budget.

- [ ] **Step 2: Implement model price table**

Use current configurable defaults stored in one JSON block so prices can be updated without changing geometry code. The initial table covers Luna, Terra and Sol.

- [ ] **Step 3: Log actual API usage**

After a response, compute estimated USD cost from returned input/output usage, append one JSONL record, and update month-to-date display.

- [ ] **Step 4: Add hard stop**

Before a request, estimate worst-case cost using configured token caps and refuse when it would exceed remaining budget.

---

### Task 8: Connect AI plan -> local solver -> editable Corel curves

**Files:**
- Modify: `corel/payload/CorelAIVectorGeometry.js`
- Modify: `corel/payload/CorelAIVectorCore.js`
- Modify: `corel/payload/CorelAIVector.html`
- Modify: `corel/tests/test_geometry.js`

**Interfaces:**
- `CAIVG.normalizePlan(plan) -> plan`
- `CAIVG.makeSegments(pathPlan, imageWidth, imageHeight) -> segments`
- `CAIV.applyPlanToSelection(app, plan, sourceMeta) -> Shape[]`

- [ ] **Step 1: Add plan-to-segment fixture tests**

Test that two consecutive G1 curve regions share the same tangent direction and that a `line` region emits a line segment rather than cubic micro-segments.

- [ ] **Step 2: Implement anchor/tangent normalization**

Clamp normalized coordinates to `[0,1]`, reject NaN/invalid region order, and merge near-duplicate anchors.

- [ ] **Step 3: Implement image-edge snapping hook**

The HTML loads the exported PNG into a hidden canvas. For every AI anchor, search within a small configurable radius for the strongest local luminance/color gradient and use that measured point when confidence is above threshold; otherwise keep the AI anchor.

- [ ] **Step 4: Implement G1 handle construction**

For smooth joins, normalize the shared tangent and calculate in/out handles from chord lengths and plan ratios. `MƯỢT HƠN` increases smooth regularization and can merge redundant curve spans; `BÁM MẪU HƠN` allows an additional anchor only when the plan permits it.

- [ ] **Step 5: Wire `AI VẼ LẠI`**

Flow:

```text
validate selection
→ export PNG
→ confirm budget/key
→ bridge geometry request
→ read JSON plan
→ local snap/solve
→ create Corel curves
→ select generated result
```

---

### Task 9: Build the one-file installer

**Files:**
- Create: `corel/installer/build_installer.py`
- Modify: `corel/tests/test_installer.py`
- Create during build: `release/CAI_COREL_AI_VECTOR_V0_1.cmd`

**Interfaces:**
- Payload marker: `__COREL_AI_VECTOR_PAYLOAD__`
- Addon folder: `<Corel Programs64>\Addons\CorelAIVector`
- Launch script copied into detected `%APPDATA%\Corel\...\Draw\Scripts` directories.

- [ ] **Step 1: Build payload ZIP in memory**

`build_installer.py` zips the payload files, computes SHA-256 and appends Base64 payload to a CMD/PowerShell bootstrap.

- [ ] **Step 2: Installer only removes its own old files**

Remove `Addons\CorelAIVector*` and `CorelAIVector*.js`; do not enumerate/delete unrelated scripts.

- [ ] **Step 3: Preserve settings**

Never delete `%LOCALAPPDATA%\CorelAIVector\api_key.dpapi`, `budget.json`, or usage logs during upgrade.

- [ ] **Step 4: Verify payload checksum before extracting**

Abort installation on SHA mismatch.

- [ ] **Step 5: Run repository-side installer tests**

Run:

```bash
python corel/tests/test_installer.py
node corel/tests/test_payload.js
node corel/tests/test_geometry.js
node corel/tests/test_schema.js
```

Expected: all PASS.

- [ ] **Step 6: Build the installer**

Run: `python corel/installer/build_installer.py`
Expected: `release/CAI_COREL_AI_VECTOR_V0_1.cmd` exists and contains the payload marker plus a valid embedded ZIP.

---

### Task 10: User-machine acceptance checkpoint

No merge to `main` before this checkpoint.

The user runs the installer on the actual Windows/CorelDRAW 2025 machine and verifies:

1. Existing Launch entries remain present.
2. `Launch > Corel AI Vector` appears.
3. Docker opens.
4. `KIỂM TRA COREL` reports v26 connection.
5. `VẼ CURVE TEST` creates a genuinely smooth editable Corel curve.
6. `XUẤT ẢNH TEST` creates the selection PNG.
7. API key can be stored/encrypted and bridge self-test passes.
8. Only then does the user set a small positive budget and run the first paid AI geometry request.

If any of steps 1-7 fail, fix host integration before spending API money.

## Self-review

- This plan does not treat pixel overlap as the drawing method.
- AI participates before curve construction and returns a structured geometry plan.
- Local code remains responsible for exact Corel coordinates and smooth Bézier construction.
- API key and budget controls are explicit and default-safe.
- The first deliverable is a real Corel installer, not another standalone PoC.
- The acceptance checkpoint deliberately tests installation and Corel curve creation before any paid API request.
