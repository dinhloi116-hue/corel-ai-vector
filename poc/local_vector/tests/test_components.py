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
    cv2.rectangle(mask, (10, 20), (50, 70), 255, -1)
    cv2.rectangle(mask, (100, 80), (180, 280), 255, -1)
    cv2.rectangle(mask, (220, 70), (350, 280), 255, -1)
    components = find_components(mask, min_area_ratio=0.005)
    selected = select_large_glyphs(components, mask.shape)
    assert len(selected) == 2
    assert all(c.h / mask.shape[0] > 0.5 for c in selected)


def test_select_large_glyphs_ignores_border_background_component():
    mask = np.zeros((300, 400), dtype=np.uint8)
    cv2.rectangle(mask, (0, 0), (399, 299), 255, 8)
    cv2.rectangle(mask, (100, 80), (180, 280), 255, -1)
    cv2.rectangle(mask, (220, 70), (350, 280), 255, -1)
    components = find_components(mask, min_area_ratio=0.005)
    selected = select_large_glyphs(components, mask.shape)
    assert len(selected) == 2
    assert all(c.x > 0 and c.y > 0 for c in selected)
