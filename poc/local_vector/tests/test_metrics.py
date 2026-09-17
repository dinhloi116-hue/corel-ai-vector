import numpy as np
from local_vector.bezier import Point, LineSegment, CubicBezier, PathGeometry
from local_vector.svg import path_to_svg_d
from local_vector.rasterize import rasterize_paths


def test_svg_contains_line_and_cubic_commands():
    path = PathGeometry([
        LineSegment(Point(0, 0), Point(10, 0)),
        CubicBezier(Point(10, 0), Point(12, 0), Point(14, 10), Point(10, 10)),
    ])
    d = path_to_svg_d(path)
    assert "L" in d
    assert "C" in d
    assert d.endswith("Z")


def test_rasterize_closed_rectangle_fills_interior():
    path = PathGeometry([
        LineSegment(Point(10, 10), Point(40, 10)),
        LineSegment(Point(40, 10), Point(40, 40)),
        LineSegment(Point(40, 40), Point(10, 40)),
        LineSegment(Point(10, 40), Point(10, 10)),
    ])
    mask = rasterize_paths([path], 60, 60)
    assert mask[25, 25] == 255
    assert mask[2, 2] == 0
    assert mask.dtype == np.uint8

import cv2
from local_vector.metrics import compare_binary_masks, compare_masks


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


def test_compare_masks_reports_closed_topology():
    ref = np.zeros((60, 60), dtype=np.uint8)
    cv2.rectangle(ref, (10, 10), (40, 40), 255, -1)
    path = PathGeometry([
        LineSegment(Point(10, 10), Point(40, 10)),
        LineSegment(Point(40, 10), Point(40, 40)),
        LineSegment(Point(40, 40), Point(10, 40)),
        LineSegment(Point(10, 40), Point(10, 10)),
    ], closed=True)
    metrics = compare_masks(ref, ref.copy(), [path])
    assert metrics.open_contours == 0
    assert metrics.self_intersections == 0
    assert metrics.node_count == 4
