from __future__ import annotations

import cv2
import numpy as np

from .bezier import CubicBezier, LineSegment, PathGeometry


def _cubic_points(segment: CubicBezier, samples: int) -> np.ndarray:
    t = np.linspace(0.0, 1.0, samples, endpoint=True)[:, None]
    omt = 1.0 - t
    p0 = np.array([segment.p0.x, segment.p0.y], dtype=np.float64)
    c1 = np.array([segment.c1.x, segment.c1.y], dtype=np.float64)
    c2 = np.array([segment.c2.x, segment.c2.y], dtype=np.float64)
    p1 = np.array([segment.p1.x, segment.p1.y], dtype=np.float64)
    return (omt**3) * p0 + 3 * (omt**2) * t * c1 + 3 * omt * (t**2) * c2 + (t**3) * p1


def _flatten_path(path: PathGeometry, samples_per_curve: int) -> np.ndarray:
    if not path.segments:
        return np.empty((0, 2), dtype=np.float64)
    pts = []
    for i, segment in enumerate(path.segments):
        if isinstance(segment, LineSegment):
            seg_pts = np.array(
                [[segment.p0.x, segment.p0.y], [segment.p1.x, segment.p1.y]],
                dtype=np.float64,
            )
        elif isinstance(segment, CubicBezier):
            seg_pts = _cubic_points(segment, samples_per_curve)
        else:
            raise TypeError(f"Unsupported segment: {type(segment)!r}")
        if i:
            seg_pts = seg_pts[1:]
        pts.append(seg_pts)
    return np.vstack(pts)


def rasterize_paths(
    paths: list[PathGeometry],
    width: int,
    height: int,
    samples_per_curve: int = 32,
) -> np.ndarray:
    canvas = np.zeros((height, width), dtype=np.uint8)
    for path in paths:
        points = _flatten_path(path, samples_per_curve)
        if len(points) < 3:
            continue
        polygon = np.rint(points).astype(np.int32).reshape(-1, 1, 2)
        layer = np.zeros_like(canvas)
        cv2.fillPoly(layer, [polygon], 255)
        # Even-odd behavior: nested contours toggle fill state.
        canvas = cv2.bitwise_xor(canvas, layer)
    return canvas
