from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from .bezier import PathGeometry, fit_path
from .cleanup import clean_glyph_mask
from .components import Component, find_components, select_large_glyphs
from .contour import extract_primary_contours
from .io import ensure_output_dir
from .metrics import VectorMetrics, compare_masks
from .rasterize import rasterize_paths
from .segmentation import segment_colored_artwork
from .svg import write_svg


def _crop_component(image: np.ndarray, component: Component) -> np.ndarray:
    return image[component.y : component.y + component.h, component.x : component.x + component.w].copy()


def _write_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Failed to write image: {path}")


def _make_overlay(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    ref = reference > 0
    cand = candidate > 0
    out = np.zeros((*reference.shape, 3), dtype=np.uint8)
    out[ref & cand] = (255, 255, 255)
    out[ref & ~cand] = (0, 0, 255)
    out[~ref & cand] = (0, 255, 0)
    return out


def _choose_two_large_glyphs(mask: np.ndarray) -> list[Component]:
    components = find_components(mask)
    candidates = select_large_glyphs(components, mask.shape)
    if len(candidates) < 2:
        raise ValueError(f"Expected at least two large glyphs, found {len(candidates)}")
    if len(candidates) > 2:
        candidates = sorted(candidates, key=lambda c: (c.h, c.area), reverse=True)[:2]
        candidates = sorted(candidates, key=lambda c: c.x)
    return candidates


def _fit_clean_mask(clean_mask: np.ndarray, max_error_px: float) -> list[PathGeometry]:
    paths: list[PathGeometry] = []
    for contour in extract_primary_contours(clean_mask):
        path = fit_path(contour, max_error_px=max_error_px)
        if path.segments:
            paths.append(path)
    return paths


def run_pipeline(
    image_bgr: np.ndarray,
    out_dir: Path,
    *,
    max_error_px: float = 1.5,
    hole_ratio: float = 0.015,
) -> dict[str, VectorMetrics]:
    out_dir = ensure_output_dir(Path(out_dir))
    full_mask = segment_colored_artwork(image_bgr)
    selected = _choose_two_large_glyphs(full_mask)
    labels = ["1", "0"]
    results: dict[str, VectorMetrics] = {}

    for glyph_label, component in zip(labels, selected, strict=True):
        glyph_dir = ensure_output_dir(out_dir / f"glyph_{glyph_label}")
        reference_crop = _crop_component(image_bgr, component)
        raw_mask = _crop_component(full_mask, component)
        clean_mask = clean_glyph_mask(raw_mask, small_hole_area_ratio=hole_ratio)

        paths = _fit_clean_mask(clean_mask, max_error_px=max_error_px)
        vector_preview = rasterize_paths(paths, component.w, component.h)
        metrics = compare_masks(clean_mask, vector_preview, paths)

        _write_image(glyph_dir / "reference_crop.png", reference_crop)
        _write_image(glyph_dir / "clean_mask.png", clean_mask)
        write_svg(paths, component.w, component.h, glyph_dir / "vector.svg")
        _write_image(glyph_dir / "vector_preview.png", vector_preview)
        _write_image(glyph_dir / "overlay.png", _make_overlay(clean_mask, vector_preview))
        _write_image(glyph_dir / "difference.png", cv2.bitwise_xor(clean_mask, vector_preview))
        (glyph_dir / "metrics.json").write_text(
            json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        results[glyph_label] = metrics

    return results
