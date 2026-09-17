# Corel AI Vector — AI-Guided Corel Tool Design

Date: 2026-09-18
Status: Approved direction after local-only PoC rejection
Repository: `dinhloi116-hue/corel-ai-vector`

## 1. Why the architecture changed

The local-only PoC achieved very high pixel overlap but still produced visibly kinked curves. That is an explicit failure for font/nameset reconstruction. Pixel IoU is therefore not the primary drawing strategy.

The production tool must use AI vision to decide **how the geometry should be built**: where true anchors belong, where corners are intentional, where long smooth curves should remain unbroken, where no anchor should be placed, and what tangent direction a Bézier span should follow. Local computer vision still performs measurement and the final geometry solver still owns exact coordinates.

The production principle is:

> **AI understands the shape; local geometry measures and constructs it.**

AI must not return an arbitrary final SVG and the local engine must not blindly trace pixels.

## 2. Target product

A real CorelDRAW 2025 / v26 tool that runs from Corel's UI and creates editable Corel Curve objects from a selected bitmap/photo.

The tool must be installable with one Windows installer file and must add exactly one safe Launch entry without deleting or replacing unrelated Launch items. Existing tools such as Refine PRO must remain untouched.

Primary workflow:

1. Select one bitmap/photo in CorelDRAW.
2. Open **Launch > Corel AI Vector**.
3. Press **AI VẼ LẠI**.
4. Tool exports the selection to a temporary PNG.
5. Local preprocessing produces a clean reference crop, masks and a coarse contour guide.
6. AI vision returns a structured geometry plan.
7. Local geometry solver snaps anchors to measured contour evidence, fits lines/cubics and enforces smoothness constraints.
8. Tool renders a preview and optionally performs one AI review pass.
9. Tool creates editable Corel Curve objects beside/on top of the source.
10. User can run **MƯỢT HƠN**, **BÁM MẪU HƠN**, or **AI SỬA LẠI** on the result.

## 3. Core architecture

### 3.1 Corel host / Docker

The UI runs as a Corel Addon browser Docker, following the proven Addons + `AppUI.xslt` / `UserUI.xslt` pattern used by prior Corel tools.

Responsibilities:

- inspect current selection
- export selection to PNG
- invoke local bridge
- show cost estimate/status
- read returned geometry JSON
- create actual Corel Curve objects using `Application.CreateCurve`, `Curve.CreateSubPath`, `SubPath.AppendLineSegment`, `SubPath.AppendCurveSegment2`/equivalent and `Layer.CreateCurve`
- preserve undo grouping
- keep source bitmap unchanged unless user explicitly deletes it

### 3.2 Local preprocessing

This stage is offline and deterministic.

Responsibilities:

- obtain source image dimensions
- segment obvious foreground/background where useful
- compute coarse outer/inner contours
- remove tiny raster noise
- detect likely counters/decorative holes
- generate an optional contour-overlay image for the AI request
- never infer design slant from camera geometry

### 3.3 AI Geometry Director

AI is not the rasterizer and not the final SVG generator. It produces a **geometry plan**.

The geometry plan must identify:

- subpaths / outer and inner contours
- semantic region type: `line`, `smooth_curve`, `sharp_corner`
- anchor locations in normalized image coordinates
- whether each anchor is required, optional, or forbidden inside a span
- tangent direction at smooth anchors
- whether adjacent curve spans must maintain G1 or G2-like smoothness
- which small features are decoration rather than glyph structure
- which counters must remain
- which regions are ambiguous and need conservative handling

### 3.4 Geometry Solver

The local solver receives the AI plan plus measured contours.

Responsibilities:

- snap normalized AI anchors to the nearest reliable contour evidence inside a bounded search window
- fit true line segments for confirmed straight regions
- fit cubic Béziers for confirmed curved spans
- optimize control-handle lengths against the measured reference
- enforce shared tangent direction at G1 joins
- optionally regularize curvature through smooth multi-span arcs
- avoid unnecessary anchors
- preserve intentional asymmetry and slant
- validate closed topology, counter retention and self-intersection

A visually kinked join is a failure even if pixel overlap is high.

## 4. Geometry plan schema

The AI output must be structured JSON. No free-form prose is accepted by the tool.

Top-level shape:

```json
{
  "version": 1,
  "glyphs": [
    {
      "id": "glyph_0",
      "label": "0",
      "confidence": 0.96,
      "paths": [
        {
          "role": "outer",
          "closed": true,
          "regions": [
            {
              "kind": "smooth_curve",
              "start": [0.50, 0.01],
              "end": [0.91, 0.43],
              "start_tangent_deg": 3.0,
              "end_tangent_deg": 72.0,
              "continuity_to_next": "g1",
              "allow_intermediate_anchor": false
            }
          ]
        }
      ],
      "decorations": []
    }
  ]
}
```

Coordinates are normalized to `[0,1]` in the crop. The geometry solver converts them to Corel document coordinates only after image-space fitting.

## 5. AI request strategy

### Pass A — geometry planning

Input:

- selected glyph/reference crop
- optional coarse contour visualization
- instructions emphasizing shape reconstruction rather than beautification

Output:

- geometry plan JSON

### Pass B — optional review

Input:

- reference crop
- rendered vector candidate
- overlay/difference image
- node/handle visualization
- current geometry plan metadata

Output:

- structured corrections such as remove/move anchor, alter tangent, merge spans, split a span, preserve a corner, or change continuity mode

Default maximum AI passes per glyph: 2.

The second pass is skipped when the user chooses economical mode and the first result meets quality gates.

## 6. Quality modes

### Tiết kiệm

- AI geometry plan: required
- AI review pass: off by default
- local solver performs refinement

### Cân bằng

- AI geometry plan: required
- one AI review pass only if local quality checks or visual heuristics detect suspicious joins

### Chính xác cao

- AI geometry plan: required
- one review pass by default
- second review pass allowed only when improvement is measurable

## 7. Cost controls

API spending must never happen silently.

Required behavior:

- API key absent by default
- monthly budget default: `0`
- user must explicitly enable paid AI
- show a cost estimate before the first paid run in a session
- record model, input/output token usage and estimated cost per request
- hard stop when user budget is reached
- maximum two AI passes per glyph unless user explicitly overrides

Default model policy:

- `gpt-5.6-luna` may be used for inexpensive classification/checks
- `gpt-5.6-terra` is the default Geometry Director because it supports image input and structured outputs while balancing cost and intelligence
- `gpt-5.6-sol` is reserved for user-selected high-accuracy retry on difficult glyphs

No image-generation model is required for reconstruction.

## 8. API key storage

The repository never contains API keys.

On Windows, the installer creates an application data directory under the user's local profile. API key storage must use Windows DPAPI through PowerShell so that the stored blob is encrypted for the current Windows user.

The Corel Docker never displays the full key after it has been saved.

## 9. Local AI bridge

Because the Corel browser environment is old and should not directly own HTTP/auth logic, the Addon invokes a local PowerShell bridge.

Bridge contract:

- input: `job.json` and source PNG path
- reads DPAPI-protected key
- sends HTTPS request to OpenAI `POST /v1/responses`
- uses image input and JSON-schema structured output
- writes `result.json`, `usage.json` and a small status file
- never modifies the Corel document

The Docker polls for completion and then applies geometry through the Corel object model.

## 10. Corel curve construction

CorelDRAW 2025 exposes the required object model methods. The implementation will construct curves in memory, create subpaths, append line/cubic segments, close paths, then create the curve on the active layer.

Requirements:

- one command group per reconstruction so Ctrl+Z removes the generated result
- no destructive modification of source bitmap
- generated curve is named with `CAIV_` metadata prefix
- inner counters are compound subpaths in the same curve where practical
- line segments remain true line segments
- smooth nodes are not represented by jagged micro-segments

## 11. UI V0.1

Compact Vietnamese Docker:

```text
Corel AI Vector

Đối tượng: 1 bitmap đã chọn

[ AI VẼ LẠI ]

Chế độ:
● Cân bằng
○ Tiết kiệm
○ Chính xác cao

☑ Tách logo/trang trí
☑ Giữ lỗ/counter thật
☑ Tối ưu đường cong mượt

[ XEM NODE AI ]
[ AI SỬA LẠI ]
[ MƯỢT HƠN ]
[ BÁM MẪU HƠN ]

Chi phí ước tính: ...
Tháng này: ... / ngân sách ...

[ API / Ngân sách ]
[ Kiểm tra cập nhật ]
```

## 12. Installer and updater

The first deliverable is one installer file for CorelDRAW 2025 / v26.

Installer requirements:

- request Administrator only when installing into Corel's Program Files Addons directory
- locate the running `CorelDRW.exe` when available; otherwise locate CorelDRAW 2025/v26 or allow manual selection
- remove only previous `CorelAIVector*` files/addon folders
- do not remove other Scripts/Addons/Launch entries
- do not touch Refine PRO
- install one Addon folder and one Launch script
- preserve user API settings and budget on upgrades

Updater requirements:

- check GitHub public repository/release metadata only when user presses **Kiểm tra cập nhật**
- show old/new version and release notes
- download only after user presses **Cập nhật**
- verify SHA-256 before replacement
- keep one rollback copy

## 13. Acceptance gates

A vector is not accepted merely because IoU is high.

Hard failures:

- visible kink on a region marked smooth
- self-intersection
- open path when closed is required
- missing structural counter
- obvious decoration fused into a master glyph when separation is enabled
- excessive anchor density on an otherwise smooth arc
- AI plan changes intentional slant/asymmetry without evidence

V0.1 installation acceptance:

- installer completes on CorelDRAW 2025/v26
- **Launch > Corel AI Vector** appears without deleting other Launch items
- Docker opens
- tool can read a selected bitmap
- tool can export a selection to PNG
- API key can be saved/encrypted and connection tested
- a fixed geometry-plan fixture can be converted to real editable Corel curves

Only after those host/integration gates pass do we enable paid AI reconstruction on the user's machine.
