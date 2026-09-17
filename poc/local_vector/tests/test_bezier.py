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


def test_nearly_straight_raster_edge_becomes_one_line():
    points = np.array([[0, 0], [10, 1], [20, 0], [30, 1], [40, 0]], dtype=np.float64)
    path = fit_path(points, max_error_px=1.5)
    assert len(path.segments) == 1
    assert isinstance(path.segments[0], LineSegment)
