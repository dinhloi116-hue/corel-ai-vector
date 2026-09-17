from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import cv2
import numpy as np

from .bezier import CubicBezier, LineSegment, PathGeometry


@dataclass(frozen=True)
class VectorMetrics:
    iou: float
    boundary_mean_px: float
    boundary_p95_px: float
    node_count: int
    open_contours: int
    self_intersections: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _binary(mask: np.ndarray) -> np.ndarray:
    return (mask > 0).astype(np.uint8) * 255


def _boundary(mask: np.ndarray) -> np.ndarray:
    binary = _binary(mask)
    kernel = np.ones((3, 3), dtype=np.uint8)
    return cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, kernel)


def _directed_boundary_distances(source_boundary: np.ndarray, target_boundary: np.ndarray) -> np.ndarray:
    src_pts = source_boundary > 0
    if not np.any(src_pts):
        return np.zeros(0, dtype=np.float64)
    if not np.any(target_boundary > 0):
        h, w = source_boundary.shape
        return np.full(int(np.count_nonzero(src_pts)), math.hypot(h, w), dtype=np.float64)
    dt_input = np.full(target_boundary.shape, 255, dtype=np.uint8)
    dt_input[target_boundary > 0] = 0
    distances = cv2.distanceTransform(dt_input, cv2.DIST_L2, 5)
    return distances[src_pts].astype(np.float64)


def compare_binary_masks(reference: np.ndarray, candidate: np.ndarray) -> VectorMetrics:
    ref = _binary(reference)
    cand = _binary(candidate)
    intersection = int(np.count_nonzero((ref > 0) & (cand > 0)))
    union = int(np.count_nonzero((ref > 0) | (cand > 0)))
    iou = 1.0 if union == 0 else intersection / union

    ref_b = _boundary(ref)
    cand_b = _boundary(cand)
    d1 = _directed_boundary_distances(ref_b, cand_b)
    d2 = _directed_boundary_distances(cand_b, ref_b)
    distances = np.concatenate([d1, d2]) if len(d1) + len(d2) else np.zeros(1)
    mean = float(np.mean(distances))
    p95 = float(np.percentile(distances, 95))
    return VectorMetrics(
        iou=float(iou),
        boundary_mean_px=mean,
        boundary_p95_px=p95,
        node_count=0,
        open_contours=0,
        self_intersections=0,
    )


def _sample_segment(segment: LineSegment | CubicBezier, samples_per_curve: int = 12) -> np.ndarray:
    if isinstance(segment, LineSegment):
        return np.array([[segment.p0.x, segment.p0.y], [segment.p1.x, segment.p1.y]], dtype=np.float64)
    t = np.linspace(0.0, 1.0, samples_per_curve)[:, None]
    omt = 1.0 - t
    p0 = np.array([segment.p0.x, segment.p0.y], dtype=np.float64)
    c1 = np.array([segment.c1.x, segment.c1.y], dtype=np.float64)
    c2 = np.array([segment.c2.x, segment.c2.y], dtype=np.float64)
    p1 = np.array([segment.p1.x, segment.p1.y], dtype=np.float64)
    return (omt**3) * p0 + 3 * (omt**2) * t * c1 + 3 * omt * (t**2) * c2 + (t**3) * p1


def _flatten_path(path: PathGeometry) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for i, segment in enumerate(path.segments):
        pts = _sample_segment(segment)
        if i:
            pts = pts[1:]
        chunks.append(pts)
    if not chunks:
        return np.empty((0, 2), dtype=np.float64)
    pts = np.vstack(chunks)
    if path.closed and len(pts) > 1 and not np.allclose(pts[0], pts[-1]):
        pts = np.vstack([pts, pts[0]])
    return pts


def _orientation(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ab = b - a
    ac = c - a
    return float(ab[0] * ac[1] - ab[1] * ac[0])


def _segments_intersect(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray, eps: float = 1e-9) -> bool:
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    return (o1 * o2 < -eps) and (o3 * o4 < -eps)


def _count_self_intersections(path: PathGeometry) -> int:
    pts = _flatten_path(path)
    if len(pts) < 4:
        return 0
    edges = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    count = 0
    for i, (a, b) in enumerate(edges):
        for j in range(i + 1, len(edges)):
            if abs(i - j) <= 1:
                continue
            if path.closed and i == 0 and j == len(edges) - 1:
                continue
            c, d = edges[j]
            if _segments_intersect(a, b, c, d):
                count += 1
    return count


def compare_masks(reference: np.ndarray, candidate: np.ndarray, paths: list[PathGeometry]) -> VectorMetrics:
    base = compare_binary_masks(reference, candidate)
    node_count = sum(len(path.segments) for path in paths)
    open_contours = sum(1 for path in paths if not path.closed)
    self_intersections = sum(_count_self_intersections(path) for path in paths)
    return VectorMetrics(
        iou=base.iou,
        boundary_mean_px=base.boundary_mean_px,
        boundary_p95_px=base.boundary_p95_px,
        node_count=node_count,
        open_contours=open_contours,
        self_intersections=self_intersections,
    )


def passes_hard_failures(
    metrics: VectorMetrics,
    *,
    counter_expected_but_missing: bool = False,
    pathological_node_limit: int | None = None,
) -> bool:
    if metrics.open_contours > 0 or metrics.self_intersections > 0:
        return False
    if counter_expected_but_missing:
        return False
    if pathological_node_limit is not None and metrics.node_count > pathological_node_limit:
        return False
    return True
