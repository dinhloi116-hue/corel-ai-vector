# Local Vector Proof-of-Concept Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove, with zero paid API calls, that a supplied nameset photo can be converted into clean editable SVG geometry for the large `1` and `0` glyphs, with measurable fidelity and low node count.

**Architecture:** Build a standalone local Python proof-of-concept under `poc/local_vector/`. It will segment the artwork from the photo, isolate target glyphs, remove small decorative holes while preserving real counters, fit clean line/cubic Bézier geometry, rasterize the candidate back for comparison, and emit SVG + overlay + difference + metrics. This PoC is deliberately isolated from the future CorelDRAW add-in; successful algorithms will later be ported into the production C# engine.

**Tech Stack:** Python 3.11+, OpenCV 4.x (`cv2`), NumPy, pytest. No OpenAI API, no cloud service, no paid dependency.

**Spec:** `docs/superpowers/specs/2026-09-17-corel-ai-vector-design.md`

## Global Constraints

- Paid API calls are forbidden in this milestone.
- The tool must not infer camera correction from glyph geometry.
- Font slant, intentional asymmetry, curved glyph contours, and intended design distortions must be preserved.
- Raster jaggies should be removed without redesigning the glyph.
- Decorative logos/holes must be separable from master glyph geometry.
- The public repository must not contain the user's private/reference source photo unless the user explicitly approves publishing it.
- Every benchmark run must emit auditable visual artifacts and machine-readable metrics.
- A high pixel-overlap score alone is insufficient; self-intersections, open contours, lost counters, or excessive node count are hard failures.

---

## File structure

Create the following focused files:

```text
poc/local_vector/
├─ README.md                         # How to run the PoC and interpret outputs
├─ requirements.txt                 # Pinned local-only dependencies
├─ run_poc.py                       # CLI orchestration only
├─ local_vector/
│  ├─ __init__.py
│  ├─ io.py                         # Image loading and artifact output
│  ├─ segmentation.py               # Artwork color/mask extraction
│  ├─ components.py                 # Connected-component and glyph candidate detection
│  ├─ cleanup.py                    # Hole/counter classification and mask cleanup
│  ├─ contour.py                    # Contour extraction and normalization
│  ├─ bezier.py                     # Line/cubic Bézier fitting
│  ├─ svg.py                        # SVG serialization
│  ├─ rasterize.py                  # Local preview rasterization from fitted segments
│  ├─ metrics.py                    # IoU, boundary error, topology and node metrics
│  └─ pipeline.py                   # Pure pipeline composition
├─ tests/
│  ├─ test_segmentation.py
│  ├─ test_components.py
│  ├─ test_cleanup.py
│  ├─ test_bezier.py
│  ├─ test_metrics.py
│  └─ test_pipeline_synthetic.py
└─ private-fixtures/
   └─ .gitkeep                      # Real reference images remain gitignored
```

Also create root `.gitignore` entries for `poc/local_vector/private-fixtures/*` except `.gitkeep`, and for generated `poc/local_vector/out/`.

---

### Task 1: Bootstrap a zero-cost local runner

**Files:**
- Create: `poc/local_vector/requirements.txt`
- Create: `poc/local_vector/run_poc.py`
- Create: `poc/local_vector/local_vector/io.py`
- Create: `poc/local_vector/local_vector/__init__.py`
- Create: `poc/local_vector/tests/test_pipeline_synthetic.py`
- Modify/Create: `.gitignore`

**Interfaces:**
- Produces: `load_image(path: Path) -> np.ndarray`
- Produces: `ensure_output_dir(path: Path) -> Path`
- Produces CLI: `python poc/local_vector/run_poc.py --input <image> --out <dir>`

- [ ] **Step 1: Write the failing IO test**

```python
from pathlib import Path
import cv2
import numpy as np
from local_vector.io import load_image, ensure_output_dir


def test_load_image_round_trip(tmp_path: Path):
    src = np.full((16, 24, 3), 127, dtype=np.uint8)
    image_path = tmp_path / "sample.png"
    assert cv2.imwrite(str(image_path), src)

    loaded = load_image(image_path)
    assert loaded.shape == (16, 24, 3)
    assert loaded.dtype == np.uint8


def test_ensure_output_dir_creates_directory(tmp_path: Path):
    out = ensure_output_dir(tmp_path / "out")
    assert out.exists()
    assert out.is_dir()
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd poc/local_vector
python -m pytest tests/test_pipeline_synthetic.py -v
```

Expected: import failure because `local_vector.io` does not yet exist.

- [ ] **Step 3: Implement minimal IO helpers**

```python
# local_vector/io.py
from pathlib import Path
import cv2
import numpy as np


def load_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Cannot read image: {path}")
    return image


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
```

- [ ] **Step 4: Add requirements and gitignore**

`requirements.txt`:

```text
opencv-python==4.13.0.92
numpy==2.2.6
pytest==8.4.2
```

Root `.gitignore` additions:

```text
poc/local_vector/private-fixtures/*
!poc/local_vector/private-fixtures/.gitkeep
poc/local_vector/out/
__pycache__/
.pytest_cache/
```

- [ ] **Step 5: Run tests**

Run the same pytest command. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .gitignore poc/local_vector
git commit -m "chore: bootstrap local vector proof of concept"
```

---

### Task 2: Segment the colored nameset artwork from a real photo

**Files:**
- Create: `poc/local_vector/local_vector/segmentation.py`
- Create: `poc/local_vector/tests/test_segmentation.py`

**Interfaces:**
- Produces: `segment_colored_artwork(image_bgr: np.ndarray) -> np.ndarray`
- Output mask contract: `uint8`, same width/height as input, values only `0` or `255`.

- [ ] **Step 1: Write a synthetic segmentation test**

```python
import cv2
import numpy as np
from local_vector.segmentation import segment_colored_artwork


def test_segment_colored_artwork_ignores_gray_background():
    image = np.full((120, 160, 3), 180, dtype=np.uint8)
    cv2.rectangle(image, (40, 30), (120, 95), (180, 120, 20), thickness=-1)

    mask = segment_colored_artwork(image)

    assert mask[60, 80] == 255
    assert mask[10, 10] == 0
    assert set(np.unique(mask)).issubset({0, 255})
```

- [ ] **Step 2: Run and confirm failure**

```bash
python -m pytest tests/test_segmentation.py -v
```

Expected: missing function/module.

- [ ] **Step 3: Implement robust saturation-based segmentation**

```python
# local_vector/segmentation.py
import cv2
import numpy as np


def segment_colored_artwork(image_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    # Colored transfer/nameset material is strongly saturated relative to
    # the ruler, mat highlights, clear carrier and neutral background.
    candidate = ((saturation >= 70) & (value >= 35)).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_OPEN, kernel, iterations=1)
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, kernel, iterations=2)
    return candidate
```

- [ ] **Step 4: Add invariants test for mask shape/type**

```python
def test_segment_mask_contract():
    image = np.zeros((30, 40, 3), dtype=np.uint8)
    mask = segment_colored_artwork(image)
    assert mask.shape == image.shape[:2]
    assert mask.dtype == np.uint8
```

- [ ] **Step 5: Run tests and commit**

```bash
python -m pytest tests/test_segmentation.py -v
git add poc/local_vector
git commit -m "feat: segment colored artwork locally"
```

---

### Task 3: Detect large glyph candidates without using OCR or AI

**Files:**
- Create: `poc/local_vector/local_vector/components.py`
- Create: `poc/local_vector/tests/test_components.py`

**Interfaces:**
- Produces dataclass: `Component(label: int, x: int, y: int, w: int, h: int, area: int)`
- Produces: `find_components(mask: np.ndarray, min_area_ratio: float = 0.002) -> list[Component]`
- Produces: `select_large_glyphs(components: list[Component], image_shape: tuple[int, int]) -> list[Component]`

- [ ] **Step 1: Write component extraction tests**

```python
import cv2
import numpy as np
from local_vector.components import find_components, select_large_glyphs


def test_find_components_returns_large_shapes_only():
    mask = np.zeros((200, 300), dtype=np.uint8)
    cv2.rectangle(mask, (20, 40), (80, 180), 255, -1)
    cv2.rectangle(mask, (120, 35), (220, 180), 255, -1)
    cv2.circle(mask, (280, 10), 2, 255, -1)

    components = find_components(mask, min_area_ratio=0.01)
    assert len(components) == 2


def test_select_large_glyphs_prefers_tall_components():
    mask = np.zeros((300, 400), dtype=np.uint8)
    cv2.rectangle(mask, (10, 20), (50, 70), 255, -1)       # small text-like
    cv2.rectangle(mask, (100, 80), (180, 280), 255, -1)    # large glyph
    cv2.rectangle(mask, (220, 70), (350, 280), 255, -1)    # large glyph
    components = find_components(mask, min_area_ratio=0.005)
    selected = select_large_glyphs(components, mask.shape)
    assert len(selected) == 2
    assert all(c.h / mask.shape[0] > 0.5 for c in selected)
```

- [ ] **Step 2: Implement connected-component extraction**

```python
from dataclasses import dataclass
import cv2
import numpy as np


@dataclass(frozen=True)
class Component:
    label: int
    x: int
    y: int
    w: int
    h: int
    area: int


def find_components(mask: np.ndarray, min_area_ratio: float = 0.002) -> list[Component]:
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = mask.shape[0] * mask.shape[1] * min_area_ratio
    result = []
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if area >= min_area:
            result.append(Component(label, int(x), int(y), int(w), int(h), int(area)))
    return result


def select_large_glyphs(components: list[Component], image_shape: tuple[int, int]) -> list[Component]:
    height, width = image_shape
    candidates = [
        c for c in components
        if c.h / height >= 0.35 and c.w / width >= 0.05
    ]
    return sorted(candidates, key=lambda c: c.x)
```

- [ ] **Step 3: Run tests and commit**

```bash
python -m pytest tests/test_components.py -v
git add poc/local_vector
git commit -m "feat: detect large glyph components"
```

---

### Task 4: Clean decorative holes while preserving real counters

**Files:**
- Create: `poc/local_vector/local_vector/cleanup.py`
- Create: `poc/local_vector/tests/test_cleanup.py`

**Interfaces:**
- Produces: `clean_glyph_mask(mask: np.ndarray, small_hole_area_ratio: float = 0.015) -> np.ndarray`
- Rule: small enclosed holes are filled; structurally large counters remain holes.

- [ ] **Step 1: Write preservation/removal tests**

```python
import cv2
import numpy as np
from local_vector.cleanup import clean_glyph_mask


def test_small_decorative_hole_is_filled():
    mask = np.zeros((200, 120), dtype=np.uint8)
    cv2.rectangle(mask, (20, 10), (100, 190), 255, -1)
    cv2.circle(mask, (60, 160), 4, 0, -1)

    cleaned = clean_glyph_mask(mask, small_hole_area_ratio=0.01)
    assert cleaned[160, 60] == 255


def test_large_counter_is_preserved():
    mask = np.zeros((200, 120), dtype=np.uint8)
    cv2.ellipse(mask, (60, 100), (45, 90), 0, 0, 360, 255, -1)
    cv2.ellipse(mask, (60, 100), (20, 60), 0, 0, 360, 0, -1)

    cleaned = clean_glyph_mask(mask, small_hole_area_ratio=0.01)
    assert cleaned[100, 60] == 0
```

- [ ] **Step 2: Implement contour-hierarchy based cleanup**

```python
import cv2
import numpy as np


def clean_glyph_mask(mask: np.ndarray, small_hole_area_ratio: float = 0.015) -> np.ndarray:
    cleaned = mask.copy()
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return cleaned

    foreground_area = max(int(cv2.countNonZero(mask)), 1)
    hierarchy = hierarchy[0]
    for idx, contour in enumerate(contours):
        parent = hierarchy[idx][3]
        if parent < 0:
            continue
        hole_area = abs(cv2.contourArea(contour))
        if hole_area / foreground_area < small_hole_area_ratio:
            cv2.drawContours(cleaned, [contour], -1, 255, thickness=-1)
    return cleaned
```

- [ ] **Step 3: Run tests and commit**

```bash
python -m pytest tests/test_cleanup.py -v
git add poc/local_vector
git commit -m "feat: separate small decoration holes from counters"
```

---

### Task 5: Fit clean line and cubic Bézier paths

**Files:**
- Create: `poc/local_vector/local_vector/contour.py`
- Create: `poc/local_vector/local_vector/bezier.py`
- Create: `poc/local_vector/tests/test_bezier.py`

**Interfaces:**
- Produces dataclasses: `Point`, `LineSegment`, `CubicBezier`, `PathGeometry`
- Produces: `extract_primary_contours(mask: np.ndarray) -> list[np.ndarray]`
- Produces: `fit_path(points: np.ndarray, max_error_px: float) -> PathGeometry`
- Hard requirement: rectangles must remain dominated by lines; smooth circles/ovals must be represented by a small set of cubics rather than many short segments.

- [ ] **Step 1: Write shape-quality tests**

```python
import cv2
import numpy as np
from local_vector.contour import extract_primary_contours
from local_vector.bezier import fit_path, LineSegment, CubicBezier


def test_rectangle_fits_to_four_lines():
    mask = np.zeros((120, 160), dtype=np.uint8)
    cv2.rectangle(mask, (20, 20), (140, 100), 255, -1)
    contour = extract_primary_contours(mask)[0]
    path = fit_path(contour, max_error_px=1.5)
    lines = [s for s in path.segments if isinstance(s, LineSegment)]
    assert len(lines) >= 4
    assert len(path.segments) <= 8


def test_ellipse_uses_few_cubic_segments():
    mask = np.zeros((200, 160), dtype=np.uint8)
    cv2.ellipse(mask, (80, 100), (55, 85), 0, 0, 360, 255, -1)
    contour = extract_primary_contours(mask)[0]
    path = fit_path(contour, max_error_px=2.0)
    cubics = [s for s in path.segments if isinstance(s, CubicBezier)]
    assert len(cubics) >= 2
    assert len(path.segments) <= 16
```

- [ ] **Step 2: Implement contour normalization**

```python
# local_vector/contour.py
import cv2
import numpy as np


def extract_primary_contours(mask: np.ndarray) -> list[np.ndarray]:
    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    contours = [c[:, 0, :].astype(np.float64) for c in contours if abs(cv2.contourArea(c)) > 4.0]
    return sorted(contours, key=lambda c: abs(cv2.contourArea(c.astype(np.float32))), reverse=True)
```

- [ ] **Step 3: Implement a two-stage fitter**

Use Douglas-Peucker only to locate candidate corners, then fit long smooth spans with cubic Béziers. Do **not** serialize every simplified polygon edge as a line.

Core types:

```python
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class LineSegment:
    p0: Point
    p1: Point


@dataclass(frozen=True)
class CubicBezier:
    p0: Point
    c1: Point
    c2: Point
    p1: Point


@dataclass
class PathGeometry:
    segments: list[LineSegment | CubicBezier]
    closed: bool = True
```

Corner detection must use local turning angle. A span whose maximum perpendicular deviation from its endpoint chord is <= `max_error_px` is emitted as a `LineSegment`; otherwise recursively fit cubic spans using chord-length parameterization and least-squares control points until the maximum error is <= `max_error_px`.

- [ ] **Step 4: Add explicit no-jagged-edge regression**

```python
def test_nearly_straight_raster_edge_becomes_one_line():
    points = np.array([[0, 0], [10, 1], [20, 0], [30, 1], [40, 0]], dtype=np.float64)
    path = fit_path(points, max_error_px=1.5)
    assert len(path.segments) == 1
    assert isinstance(path.segments[0], LineSegment)
```

- [ ] **Step 5: Run tests and commit**

```bash
python -m pytest tests/test_bezier.py -v
git add poc/local_vector
git commit -m "feat: fit clean line and bezier geometry"
```

---

### Task 6: Serialize SVG and rasterize the candidate locally

**Files:**
- Create: `poc/local_vector/local_vector/svg.py`
- Create: `poc/local_vector/local_vector/rasterize.py`
- Create: `poc/local_vector/tests/test_metrics.py`

**Interfaces:**
- Produces: `path_to_svg_d(path: PathGeometry) -> str`
- Produces: `write_svg(paths: list[PathGeometry], width: int, height: int, output: Path) -> None`
- Produces: `rasterize_paths(paths: list[PathGeometry], width: int, height: int, samples_per_curve: int = 32) -> np.ndarray`

- [ ] **Step 1: Write SVG command test**

```python
from local_vector.bezier import Point, LineSegment, CubicBezier, PathGeometry
from local_vector.svg import path_to_svg_d


def test_svg_contains_line_and_cubic_commands():
    path = PathGeometry([
        LineSegment(Point(0, 0), Point(10, 0)),
        CubicBezier(Point(10, 0), Point(12, 0), Point(14, 10), Point(10, 10)),
    ])
    d = path_to_svg_d(path)
    assert "L" in d
    assert "C" in d
    assert d.endswith("Z")
```

- [ ] **Step 2: Implement SVG serialization**

Format floats to at most three decimals, emit `M`, `L`, `C`, and `Z`, use `fill="#000"`, no stroke, and preserve holes with `fill-rule="evenodd"`.

- [ ] **Step 3: Implement local rasterization**

Flatten each cubic into 32 sampled points, concatenate closed polygons, and fill via `cv2.fillPoly`. This avoids adding a browser/render dependency in the PoC.

- [ ] **Step 4: Run tests and commit**

```bash
python -m pytest tests/test_metrics.py -v
git add poc/local_vector
git commit -m "feat: export and rasterize vector candidates"
```

---

### Task 7: Add objective fidelity and topology metrics

**Files:**
- Create: `poc/local_vector/local_vector/metrics.py`
- Modify: `poc/local_vector/tests/test_metrics.py`

**Interfaces:**
- Produces dataclass: `VectorMetrics(iou, boundary_mean_px, boundary_p95_px, node_count, open_contours, self_intersections)`
- Produces: `compare_masks(reference: np.ndarray, candidate: np.ndarray, paths: list[PathGeometry]) -> VectorMetrics`

- [ ] **Step 1: Write perfect-match and shifted-match tests**

```python
import cv2
import numpy as np
from local_vector.metrics import compare_binary_masks


def test_identical_masks_have_iou_one():
    a = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(a, (20, 20), (80, 80), 255, -1)
    metrics = compare_binary_masks(a, a.copy())
    assert metrics.iou == 1.0
    assert metrics.boundary_mean_px == 0.0


def test_shifted_mask_scores_worse():
    a = np.zeros((100, 100), dtype=np.uint8)
    b = np.zeros_like(a)
    cv2.rectangle(a, (20, 20), (80, 80), 255, -1)
    cv2.rectangle(b, (25, 20), (85, 80), 255, -1)
    metrics = compare_binary_masks(a, b)
    assert metrics.iou < 1.0
    assert metrics.boundary_mean_px > 0.0
```

- [ ] **Step 2: Implement IoU and symmetric boundary distance**

Use XOR/intersection/union for IoU. For boundary error, derive 1-pixel boundaries with morphological gradient and use `cv2.distanceTransform` in both directions; report mean and 95th percentile.

- [ ] **Step 3: Implement hard-failure checks**

A result cannot PASS when any of these are true:

```text
open_contours > 0
self_intersections > 0
counter_expected_but_missing == true
node_count is pathological relative to contour complexity
```

- [ ] **Step 4: Run tests and commit**

```bash
python -m pytest tests/test_metrics.py -v
git add poc/local_vector
git commit -m "feat: measure vector fidelity and topology"
```

---

### Task 8: Compose the end-to-end PALMER `1`/`0` benchmark

**Files:**
- Create: `poc/local_vector/local_vector/pipeline.py`
- Modify: `poc/local_vector/run_poc.py`
- Create: `poc/local_vector/README.md`
- Create: `poc/local_vector/private-fixtures/.gitkeep`

**Interfaces:**
- Produces: `run_pipeline(image_bgr: np.ndarray, out_dir: Path) -> dict[str, VectorMetrics]`
- CLI artifacts per glyph:
  - `glyph_1/reference_crop.png`
  - `glyph_1/clean_mask.png`
  - `glyph_1/vector.svg`
  - `glyph_1/vector_preview.png`
  - `glyph_1/overlay.png`
  - `glyph_1/difference.png`
  - `glyph_1/metrics.json`
  - same set for `glyph_0/`

- [ ] **Step 1: Write pipeline composition test using a synthetic `10` image**

```python
import cv2
import numpy as np
from pathlib import Path
from local_vector.pipeline import run_pipeline


def test_pipeline_emits_two_glyph_artifact_sets(tmp_path: Path):
    image = np.full((500, 700, 3), 160, dtype=np.uint8)
    color = (180, 120, 20)
    cv2.rectangle(image, (100, 80), (220, 430), color, -1)
    cv2.ellipse(image, (470, 250), (130, 180), 0, 0, 360, color, -1)
    cv2.ellipse(image, (470, 250), (60, 115), 0, 0, 360, (160, 160, 160), -1)

    result = run_pipeline(image, tmp_path)
    assert len(result) == 2
    assert any(tmp_path.rglob("vector.svg"))
    assert any(tmp_path.rglob("metrics.json"))
```

- [ ] **Step 2: Implement pipeline composition**

The pipeline must call, in order:

```text
segment_colored_artwork
→ find_components
→ select_large_glyphs
→ crop component
→ clean_glyph_mask
→ extract_primary_contours
→ fit_path
→ write_svg
→ rasterize_paths
→ compare_masks
→ write overlay/difference/metrics
```

No network or API function may be imported by `pipeline.py`.

- [ ] **Step 3: Add CLI arguments**

```text
--input PATH          required
--out PATH            required
--max-error-px FLOAT  default 1.5
--hole-ratio FLOAT    default 0.015
```

- [ ] **Step 4: Document how to stage the real PALMER image privately**

README command:

```bash
cp /path/to/palmer-reference.png poc/local_vector/private-fixtures/palmer.png
python poc/local_vector/run_poc.py \
  --input poc/local_vector/private-fixtures/palmer.png \
  --out poc/local_vector/out/palmer
```

State explicitly that `private-fixtures/` is ignored because the GitHub repo is public.

- [ ] **Step 5: Run the real PALMER benchmark locally**

Use the conversation-provided reference image as the input without committing it to GitHub.

Expected deliverables for both large glyphs:

```text
reference_crop.png
clean_mask.png
vector.svg
vector_preview.png
overlay.png
difference.png
metrics.json
```

- [ ] **Step 6: Evaluate the hard gate**

The PoC is considered technically promising only if both large glyphs satisfy all topology rules and the visual overlay shows no obvious redesign of the source shape.

Initial numeric target for this benchmark:

```text
IoU >= 0.97
boundary_mean_px <= 2.0
boundary_p95_px <= 5.0
open_contours == 0
self_intersections == 0
```

These numeric thresholds are benchmark gates, not permission to ignore visually wrong geometry. The user must still inspect the SVG/overlay before the project advances to Corel integration.

- [ ] **Step 7: Run all tests**

```bash
cd poc/local_vector
python -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add poc/local_vector .gitignore
git commit -m "feat: complete zero-cost local vector benchmark"
```

---

## Milestone acceptance decision

After Task 8, stop. Do not start CorelDRAW integration and do not add an OpenAI API client yet.

Present the user with the two `vector.svg` files plus their overlay/difference images and metrics. The user decides whether the geometry is good enough to proceed.

If accepted, the next separate implementation plan will cover **CorelDRAW integration + reusable production C# engine**. If rejected, continue improving only the local reconstruction algorithm until the benchmark is satisfactory.

## Self-review

- Spec coverage for Milestone 0: local-only reconstruction, no paid API, preserve slant/asymmetry, separate decoration/counters, low-node Bézier output, objective QA, and user visual approval are all represented.
- No OpenAI/API dependency appears in implementation tasks.
- Real source image is explicitly excluded from the public repository.
- Interfaces used by later tasks match the signatures defined earlier.
- No Corel plugin work is included before proof-of-concept approval.
