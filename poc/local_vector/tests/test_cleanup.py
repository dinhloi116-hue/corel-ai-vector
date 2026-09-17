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
