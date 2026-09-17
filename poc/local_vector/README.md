# Local Vector Proof of Concept

This milestone proves raster/photo-to-vector reconstruction **without any paid API**. It uses only OpenCV, NumPy, and local Python code.

## Run

```bash
python -m pip install -r poc/local_vector/requirements.txt
cp /path/to/palmer-reference.png poc/local_vector/private-fixtures/palmer.png
python poc/local_vector/run_poc.py \
  --input poc/local_vector/private-fixtures/palmer.png \
  --out poc/local_vector/out/palmer
```

Optional controls:

```text
--max-error-px FLOAT  Bézier/line fitting tolerance, default 1.5
--hole-ratio FLOAT    Fill small enclosed decoration holes, default 0.015
```

`private-fixtures/` is gitignored because this repository is public. Do not commit customer/reference photos without explicit permission.

## Artifacts

Each detected large glyph produces:

- `reference_crop.png` — original photo crop
- `clean_mask.png` — local segmentation after small decorative holes are removed
- `vector.svg` — editable SVG geometry
- `vector_preview.png` — local rasterization of the SVG geometry
- `overlay.png` — white overlap, red reference-only, green vector-only
- `difference.png` — binary geometry difference
- `metrics.json` — IoU, boundary error, node count, and topology checks

## Benchmark gate

The initial target for both large PALMER glyphs is:

```text
IoU >= 0.97
boundary_mean_px <= 2.0
boundary_p95_px <= 5.0
open_contours == 0
self_intersections == 0
```

The numbers are only a gate. The overlay and SVG still require visual inspection before CorelDRAW integration begins.
