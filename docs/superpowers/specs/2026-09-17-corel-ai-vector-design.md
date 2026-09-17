# Corel AI Vector — V1 Design Specification

Date: 2026-09-17
Status: Approved design, pre-implementation
Repository: `dinhloi116-hue/corel-ai-vector`

## 1. Goal

Build a CorelDRAW tool that can reconstruct sports fonts, namesets, numbers, logos, patches, and similar flat graphic references from raster images or photos into clean editable vector curves.

The core product requirement is not "AI image generation". The tool must reconstruct geometry from a supplied reference image while preserving the original design characteristics such as slant, asymmetry, curved text layout, counters, sharp corners, and intended distortions.

The first proof-of-concept must work without any paid API calls.

## 2. Primary user workflow

1. User selects a bitmap in CorelDRAW.
2. User presses **PHÂN TÍCH & VẼ VECTOR**.
3. The local engine analyzes source type and image quality.
4. Camera distortion is corrected only when reliable physical references exist.
5. Graphic content is segmented into glyphs, numbers, logos, decoration, and layout data.
6. Local geometry reconstruction produces clean lines, corners, and Bézier curves.
7. Optional AI review can inspect difficult results, but is disabled by default.
8. The tool creates editable CorelDRAW Curve objects plus the original layout reconstruction.

## 3. Hard geometry rules

The tool must never assume "straight is correct".

- Camera distortion may be corrected.
- Font italic/slant must be preserved.
- Curved glyph contours must be preserved.
- Curved text layout must be preserved and stored separately from glyph geometry.
- Intentional asymmetry must be preserved.
- Envelope/warp must be detected and retained as layout/design deformation, not silently normalized.
- Raster jaggies must be removed.
- Decorative logos inside glyphs must be separable from the master glyph.
- Repeated copies of the same glyph may be fused only when geometric consistency is high.

The engine must not infer camera correction from glyph geometry when the glyph may itself be stylized, italic, condensed, skewed, asymmetric, or intentionally distorted.

## 4. Source analysis

The analyzer classifies each input as one or more of:

- clean raster
- scan
- photo
- screenshot
- printed/transfer reference

It also detects:

- text
- numbers
- logos
- decorative graphics
- ruler
- cutting-grid or physical grid
- sheet/film/paper edges
- repeated glyphs

## 5. Camera correction

Camera correction is a separate stage and must not alter the design style.

Preferred physical references, in order:

1. physical grid
2. ruler
3. paper/transfer-film edges
4. rectangular physical frame
5. other reliable non-glyph reference lines

Possible corrections:

- lens distortion correction when sufficiently detectable
- rotation correction
- perspective rectification / homography

If reliable physical references do not exist, automatic perspective correction is skipped. The tool must prefer preserving the original raster geometry over guessing from the letters themselves.

## 6. Glyph geometry vs layout geometry

The internal data model separates:

### Glyph geometry
The shape of `P`, `A`, `0`, `1`, etc.

### Layout geometry
Position, rotation, spacing, baseline curve, word arc, and overall arrangement.

For curved namesets the tool must be able to output both:

- clean master glyph candidates
- the reconstructed original curved layout

If a glyph is itself warped by an envelope, it is marked as `WARPED` and is not automatically treated as a clean font master.

## 7. Repeated glyph fusion

When the same glyph appears at multiple physical sizes or locations, the tool should normalize and compare them.

Example: a large `1` and small `1` from the same nameset can help reconstruct one `MASTER_1` by reducing photographic and cutting noise.

Fusion must consider:

- normalized contour similarity
- counter similarity
- slant consistency
- characteristic corner locations
- source quality

If sources differ too much, they remain separate variants rather than being merged automatically.

## 8. Local vector reconstruction

The local engine is the primary drawing engine and must work with API disabled.

Pipeline:

1. image/mask extraction
2. edge extraction
3. contour hierarchy analysis
4. outer vs inner contour classification
5. raster-noise filtering
6. segmentation into line / corner / curve regions
7. line fitting
8. cubic Bézier fitting
9. path closure and topology validation
10. node simplification
11. render-back comparison

The target is not minimum node count at any cost. The target is accurate geometry with the fewest nodes necessary to preserve the design.

A nearly straight raster edge should become a true line segment rather than a polyline that follows every pixel irregularity.

## 9. Decorative element handling

Elements such as a crest or logo embedded inside a number are not automatically part of the master glyph.

User-facing behavior should support:

- remove decoration and restore glyph face
- separate decoration into its own object
- keep decoration embedded in the layout copy

The master glyph should remain clean when the decoration is not structurally part of the numeral/letter.

## 10. Optional AI review

AI is an optional reviewer, not the main vectorizer.

Default state on first install:

- AI review: OFF
- monthly API budget: 0

The local engine runs first. AI may be used only when the user enables it, selects a high-accuracy mode, or explicitly asks to review a difficult glyph.

AI input may include:

- reference crop
- candidate vector preview
- geometry metadata
- repeated glyph references

AI output must be structured JSON, not free-form prose.

Example correction categories:

- candidate region too wide/narrow
- curve starts too early/late
- preserve sharp corner
- straighten confirmed line segment
- counter proportion mismatch
- unnecessary nodes

AI must not redesign the glyph, substitute a font, or generate arbitrary SVG.

## 11. Confidence and pass/fail

A single bitmap overlap percentage is insufficient.

Each glyph should be evaluated across:

- shape accuracy
- geometry quality
- topology
- node efficiency
- source confidence

Hard failures override a high similarity score:

- self-intersection
- open contour where a closed contour is required
- missing counter
- accidental component merge
- decoration incorrectly fused into a glyph when separation is requested
- perspective correction alters intentional slant/style
- abnormal node explosion

Suggested quality states:

- PASS
- REVIEW
- LOW CONFIDENCE
- DIFFICULT

Exact scoring weights and thresholds will be calibrated from the proof-of-concept benchmark rather than treated as fixed truths before testing.

## 12. API cost controls

API spending must be impossible by accident.

Required controls:

- API disabled by default
- default monthly budget = 0
- optional explicit monthly budget
- optional warning threshold
- optional hard stop at budget limit
- per-task cost logging
- token/model/call-count logging
- estimate before high-cost review modes

The tool must remain useful offline for local vector reconstruction.

## 13. CorelDRAW UI

The V1 dock panel should remain compact.

Primary controls:

- **PHÂN TÍCH & VẼ VECTOR**
- **XEM SO SÁNH**
- **AUTO FIX**
- **HOÀN TÁC KẾT QUẢ**

Advanced options:

- keep original layout
- create master glyphs
- separate logo/decoration
- reduce nodes
- AI review
- quality preset: fast / balanced / high accuracy
- maximum AI passes

System controls:

- API settings
- check for updates
- restore previous version
- current version display

Per-glyph actions:

- compare this glyph
- auto-fix this glyph
- set as master
- exclude from master

## 14. CorelDRAW output

For a nameset image such as `PALMER 10`, the tool should create layers similar to:

- `01_REFERENCE`
- `02_MASTER_GLYPHS`
- `03_DECORATION`
- `04_ORIGINAL_LAYOUT`
- `05_DIFFERENCE` (optional QA)

Each glyph should be a real editable CorelDRAW Curve object.

Useful metadata may include:

- glyph identifier
- source confidence
- master source count
- node count
- perspective corrected: yes/no
- AI reviewed: yes/no

## 15. Technical architecture

V1 preferred architecture: C#-first.

Primary projects:

- `CorelAIVector.Addin`
- `CorelAIVector.Engine`
- `CorelAIVector.Models`
- `CorelAIVector.AI` (optional path)
- `CorelAIVector.Updater`
- `CorelAIVector.Installer`

Likely image-processing dependency:

- OpenCvSharp

The Corel add-in is responsible only for Corel-specific integration and should not own image-processing or AI logic.

The engine should remain testable outside CorelDRAW.

## 16. Internal vector model

The engine should use its own vector representation before generating Corel curves.

Conceptual segment types:

- line
- cubic Bézier
- corner/cusp node

A path stores:

- closed/open state
- ordered segments
- contour role (outer/counter/decoration)
- normalized bounds
- metadata

This abstraction allows later export to SVG, Corel curves, and potentially font-source formats without rewriting the reconstruction engine.

## 17. Repository layout

Proposed structure after implementation begins:

```text
corel-ai-vector/
├─ src/
│  ├─ CorelAIVector.Addin/
│  ├─ CorelAIVector.Engine/
│  ├─ CorelAIVector.Models/
│  ├─ CorelAIVector.AI/
│  ├─ CorelAIVector.Updater/
│  └─ CorelAIVector.Installer/
├─ tests/
│  ├─ Engine.Tests/
│  ├─ Vector.Tests/
│  └─ TestImages/
├─ prompts/
├─ docs/
├─ samples/
├─ build/
└─ README.md
```

## 18. Update system

The repository is public.

The installed tool should include a manual **KIỂM TRA CẬP NHẬT** action.

Update flow:

1. check published version information
2. compare installed version
3. show available version and brief changes
4. user explicitly chooses update
5. download update package
6. verify SHA-256
7. backup current installation
8. replace tool files
9. restart/reload as required

Rollback must restore the previous working version.

API keys must never be committed to the public repository. Local credentials should be stored using a Windows-protected mechanism such as DPAPI or Windows Credential Manager.

## 19. Delivery strategy

The project must use a proof-first implementation order.

### Milestone 0 — Local vector proof of concept
Cost: 0 API

Use the existing `PALMER 10` reference image.

Initial benchmark targets:

1. reconstruct large `0`
2. reconstruct large `1`
3. compare large/small `0`
4. compare large/small `1`
5. output SVG
6. output reference/vector overlay
7. output difference visualization
8. report node count and topology checks

The proof-of-concept is considered useful only if the reconstructed curves are visually faithful, smooth, editable, and materially cleaner than raw tracing.

If tests 1–4 do not produce convincing geometry, the project stops and the local engine is revised before Corel integration or API work begins.

### Milestone 1 — Corel integration

After the local vector engine is accepted:

- select bitmap in Corel
- run reconstruction
- create editable Curve objects
- create reference/vector QA layers

### Milestone 2 — Glyph and layout automation

- automatic glyph splitting
- master glyph management
- curved text layout reconstruction
- repeated glyph fusion
- decoration separation

### Milestone 3 — Optional AI review

Only after local reconstruction is already useful:

- structured geometry review
- explicit user-controlled API spending
- high-accuracy mode

### Milestone 4 — Installer and updater

- one-step installation target
- update button
- rollback
- versioned GitHub releases

## 20. Initial acceptance criteria

Before any paid API integration, the proof-of-concept must demonstrate on the `PALMER 10` test image that:

- `0` outer contour is faithfully reconstructed
- `0` inner counter is faithfully reconstructed
- `1` characteristic top, stem, and foot geometry are preserved
- embedded decoration can be excluded from the master numeral
- curves are smooth rather than pixel-following
- obvious straight regions are true lines where justified
- no required contours are open
- no self-intersections exist
- node count is reasonable for the geometric complexity
- large and small copies of the same glyph are geometrically consistent after normalization
- SVG opens as editable vector geometry

The user visually approves the proof before the project proceeds to Corel plugin development.

## 21. Explicitly out of scope for the first proof

The first proof does not include:

- OpenAI API calls
- OTF/TTF generation
- automatic A–Z font completion
- automatic online updater
- full Corel docking UI
- installer packaging

Those are subsequent milestones only after reconstruction quality is proven.
