from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
import cv2


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


def _point(p: np.ndarray) -> Point:
    return Point(float(p[0]), float(p[1]))


def _is_closed(points: np.ndarray, max_error_px: float) -> bool:
    if len(points) < 4:
        return False
    # Open synthetic strokes normally have distant endpoints; contours returned
    # by OpenCV have neighboring first/last samples even though the first sample
    # is not duplicated at the end.
    return float(np.linalg.norm(points[0] - points[-1])) <= max(2.5, 2.0 * max_error_px)


def _line_deviation(points: np.ndarray) -> float:
    if len(points) <= 2:
        return 0.0
    a = points[0]
    b = points[-1]
    ab = b - a
    denom = float(np.linalg.norm(ab))
    if denom <= 1e-12:
        return float(np.max(np.linalg.norm(points - a, axis=1)))
    cross = np.abs(ab[0] * (a[1] - points[:, 1]) - ab[1] * (a[0] - points[:, 0]))
    return float(np.max(cross / denom))


def _chord_params(points: np.ndarray) -> np.ndarray:
    if len(points) == 1:
        return np.zeros(1, dtype=np.float64)
    d = np.linalg.norm(np.diff(points, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(d)])
    if s[-1] <= 1e-12:
        return np.linspace(0.0, 1.0, len(points))
    return s / s[-1]


def _eval_cubic(p0: np.ndarray, c1: np.ndarray, c2: np.ndarray, p3: np.ndarray, t: np.ndarray) -> np.ndarray:
    t = np.asarray(t, dtype=np.float64)[:, None]
    omt = 1.0 - t
    return (
        (omt ** 3) * p0
        + 3.0 * (omt ** 2) * t * c1
        + 3.0 * omt * (t ** 2) * c2
        + (t ** 3) * p3
    )


def _fit_single_cubic(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, int]:
    p0 = points[0]
    p3 = points[-1]
    t = _chord_params(points)
    b0 = (1.0 - t) ** 3
    b1 = 3.0 * (1.0 - t) ** 2 * t
    b2 = 3.0 * (1.0 - t) * t ** 2
    b3 = t ** 3
    rhs = points - b0[:, None] * p0 - b3[:, None] * p3
    A = np.column_stack([b1, b2])
    try:
        controls, _, _, _ = np.linalg.lstsq(A, rhs, rcond=None)
        c1, c2 = controls[0], controls[1]
    except np.linalg.LinAlgError:
        delta = (p3 - p0) / 3.0
        c1, c2 = p0 + delta, p0 + 2.0 * delta
    fitted = _eval_cubic(p0, c1, c2, p3, t)
    errors = np.linalg.norm(fitted - points, axis=1)
    split = int(np.argmax(errors))
    return c1, c2, float(errors[split]), split


def _fit_span(points: np.ndarray, max_error_px: float, depth: int = 0) -> list[LineSegment | CubicBezier]:
    if len(points) < 2:
        return []
    if _line_deviation(points) <= max_error_px:
        return [LineSegment(_point(points[0]), _point(points[-1]))]
    if len(points) <= 4 or depth >= 14:
        c1, c2, _, _ = _fit_single_cubic(points)
        return [CubicBezier(_point(points[0]), _point(c1), _point(c2), _point(points[-1]))]
    c1, c2, error, split = _fit_single_cubic(points)
    if error <= max_error_px:
        return [CubicBezier(_point(points[0]), _point(c1), _point(c2), _point(points[-1]))]
    # Keep enough data on each side for a stable least-squares fit.
    split = max(2, min(len(points) - 3, split))
    left = _fit_span(points[: split + 1], max_error_px, depth + 1)
    right = _fit_span(points[split:], max_error_px, depth + 1)
    return left + right


def _turning_angle_deg(prev: np.ndarray, cur: np.ndarray, nxt: np.ndarray) -> float:
    v1 = cur - prev
    v2 = nxt - cur
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 <= 1e-12 or n2 <= 1e-12:
        return 0.0
    cosv = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
    return math.degrees(math.acos(cosv))


def _corner_indices(points: np.ndarray, max_error_px: float) -> list[int]:
    contour = points.astype(np.float32).reshape(-1, 1, 2)
    epsilon = max(1.0, max_error_px * 1.15)
    approx = cv2.approxPolyDP(contour, epsilon, True)[:, 0, :].astype(np.float64)
    if len(approx) < 3:
        return []
    corners: list[int] = []
    for i, cur in enumerate(approx):
        angle = _turning_angle_deg(approx[i - 1], cur, approx[(i + 1) % len(approx)])
        # Real typographic corners are markedly sharper than vertices introduced
        # merely to approximate a smooth oval.
        if angle >= 38.0:
            idx = int(np.argmin(np.linalg.norm(points - cur, axis=1)))
            corners.append(idx)
    return sorted(set(corners))


def _cyclic_span(points: np.ndarray, start: int, end: int) -> np.ndarray:
    n = len(points)
    if start <= end:
        return points[start : end + 1]
    return np.vstack([points[start:], points[: end + 1]])


def _quarter_indices(points: np.ndarray) -> list[int]:
    closed = np.vstack([points, points[0]])
    d = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(d)])
    total = cum[-1]
    if total <= 1e-12:
        return [0]
    idxs = []
    for frac in (0.0, 0.25, 0.5, 0.75):
        target = frac * total
        idxs.append(min(int(np.searchsorted(cum, target)), len(points) - 1))
    return sorted(set(idxs))


def fit_path(points: np.ndarray, max_error_px: float) -> PathGeometry:
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("points must be an Nx2 array")
    if len(pts) < 2:
        return PathGeometry([], closed=False)

    closed = _is_closed(pts, max_error_px)
    if not closed:
        return PathGeometry(_fit_span(pts, max_error_px), closed=False)

    corners = _corner_indices(pts, max_error_px)
    split_indices = corners if len(corners) >= 2 else _quarter_indices(pts)
    if len(split_indices) < 2:
        return PathGeometry(_fit_span(np.vstack([pts, pts[0]]), max_error_px), closed=True)

    segments: list[LineSegment | CubicBezier] = []
    for i, start in enumerate(split_indices):
        end = split_indices[(i + 1) % len(split_indices)]
        span = _cyclic_span(pts, start, end)
        if i == len(split_indices) - 1 and len(span) and not np.allclose(span[-1], pts[split_indices[0]]):
            span = np.vstack([span, pts[split_indices[0]]])
        segments.extend(_fit_span(span, max_error_px))
    return PathGeometry(segments, closed=True)
